"""Command to help users assume roles in different accounts."""
# See docs/assume.md for more information.

import os
from getpass import getuser
from uuid import uuid1

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import click

from lib import config, helpers  # pylint: disable=no-name-in-module

ROLE_FORMAT = "arn:aws:iam::{account_id}:role/{role}"
URL_FORMAT = "https://signin.aws.amazon.com/switchrole?account={account_id}&roleName={role_name}&displayName={account}%20-%20{role}"  # pylint: disable=line-too-long
OVERWRITE_ENVS = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]
AWS_PROFILE = os.environ.get("AWS_PROFILE", "default")


# pylint: disable=too-many-arguments,too-many-locals,line-too-long,too-many-statements
@click.command()
@click.argument("account", envvar="NEOTK_ASSUME_ACCOUNT", required=False)
@click.argument("role", envvar="NEOTK_ASSUME_ROLE", required=False)
@click.option("--duration", "-d", envvar="NEOTK_ASSUME_DURATION", default='1h',
              help="Duration in seconds or with units (h, m, s)")
@click.option("--token", "-t", help="MFA token")
@click.option("--session-name", "-s", help="Desired session name", envvar="NEOTK_ASSUME_SESSION")
@click.option("--url", default=False, is_flag=True,
              help="Provide URL instead of environment variables")
@click.option("--list-only", "-l", default=False, is_flag=True,
              help="Output list of possible accounts and roles")
@click.option("--list-all", "-a", default=False, is_flag=True,
              help="Output the entire list of possible accounts and roles")
def handle(account, role, duration, token, session_name, url, list_only, list_all):
    """Switch between roles in Neo accounts with MFA.

    ACCOUNT and ROLE can be configured in config.py as aliases. Will default to AWS account ID
    and role name.

    Environment variables HECLI_ASSUME_ACCOUNT, HECLI_ASSUME_ROLE, and HECLI_ASSUME_DURATION
    can be used to specify default values for assume.

    USAGE:

    $ `hecli assume sit poweruser` && aws s3 ls  # Use pre-defined account and role aliases

    $ `hecli assume 123567890123456 NeoDevopsPoweruser` && aws s3 ls  # Use account ID and role name

    $ `hecli assume sit poweruser -t 123456`  # Provide an MFA token
    """

    session = boto3.Session(profile_name=AWS_PROFILE)

    if list_all:
        _list_only(None)
        exit(0)

    if list_only:
        _list_only(account)
        exit(0)

    account, role, token = _get_args(account, role, token, url)

    if not all([account, role]):
        click.echo("You must provide ACCOUNT, and ROLE to continue", err=True)
        exit(1)

    os.environ = {k: v
                  for k, v in os.environ.items()
                  if os.environ[k] in OVERWRITE_ENVS}

    if account in config.NEO_ACCOUNTS:
        # Try to use account_id, else default to argument value
        account_id = config.NEO_ACCOUNTS[account].get("account_id", account)
        # Try to use available_roles[role] else use argument value
        role_name = config.NEO_ACCOUNTS[account].get("available_roles", {}).get(role, role)
    else:
        account_id = account
        role_name = role

    if url:
        click.echo(URL_FORMAT.format(account_id=account_id,
                                     account=account,
                                     role_name=role_name,
                                     role=role), err=True)
        exit(0)

    duration = helpers.str_to_seconds(duration)
    role_arn = ROLE_FORMAT.format(account_id=account_id, role=role_name)

    click.echo(f"# Assuming {role_arn}", err=True)

    if not session_name:
        session_name = ("%s_neotk_assume_%s" % (getuser(), str(uuid1())))[:64]

    assume_args = {
        "RoleArn": role_arn,
        "RoleSessionName": session_name,
        "DurationSeconds": duration,
    }

    sts = session.client("sts")

    try:
        username = sts.get_caller_identity().get("Arn", "").split("/")[-1]

        if not username:
            click.echo("# Error getting identity", err=True)
            exit(1)

        iam = session.client("iam")
        devices = iam.list_mfa_devices(UserName=username)

        assume_args["SerialNumber"] = devices["MFADevices"][0]["SerialNumber"]
        assume_args["TokenCode"] = token
        tokens = sts.assume_role(**assume_args)
    except ClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        exit(1)
    except NoCredentialsError as exc:
        click.echo(f"Error: {exc}.\nDid run aws configure?", err=True)
        exit(1)
    except KeyError:
        click.echo("# Check that MFA is enabled.")
        exit(1)

    click.echo(f"export AWS_ACCESS_KEY_ID={tokens['Credentials']['AccessKeyId']}")
    click.echo(f"export AWS_SECRET_ACCESS_KEY={tokens['Credentials']['SecretAccessKey']}")
    click.echo(f"export AWS_SESSION_TOKEN={tokens['Credentials']['SessionToken']}")
    click.echo(f"export TF_VAR_env={account}")
    click.echo("# Session expires: %s (%d seconds)" % (
        tokens["Credentials"]["Expiration"].isoformat(),
        duration), err=True)


def _list_only(account):
    """List accounts and roles"""
    for _account, account_info in config.NEO_ACCOUNTS.items():
        if account and account != _account:
            continue

        click.echo("Account: %s (%s)" % (_account, account_info.get("account_id")), err=True)
        for _role, role_name in account_info.get("available_roles").items():
            click.echo("  Role: %s (%s)" % (_role, role_name), err=True)


def _get_args(account, role, token, url):
    """Prompt the user for input if we don't have them over STDERR so that it works in $()"""
    if not account:
        account = click.prompt("Account", err=True)

    if not role:
        role = click.prompt("Role", err=True)

    if not token and not url:
        token = click.prompt("MFA Token", err=True)

    return account, role, token
