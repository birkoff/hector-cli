import click
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from lib import config  # pylint: disable=no-name-in-module
from getpass import getuser
from uuid import uuid1
import os


@click.command()
# pylint: disable=too-many-arguments,too-many-locals,line-too-long,too-many-statements
@click.argument("account", required=False)
@click.argument("role", required=False)
@click.option("--token", "-t", help="MFA token", required=False)
def handle(account, role, token):
    client = generate_client(account, role, token)
    i = 0
    next_token = None
    while 0 == i or next_token:
        i = i + 1
        response = list_all_secrets(client, next_token)
        secrets_list = response.get('SecretList', [])
        next_token = response.get('NextToken', None)
        for secret in secrets_list:
            secret_name = secret.get('Name')
            secret_description = secret.get('Description', 'No description available')
            secret_last_retrival = secret.get('LastAccessedDate')
            click.echo("{}, {}, {}".format(secret_last_retrival, secret_name, secret_description))


def list_all_secrets(client, next_token):
    if next_token:
        response = client.list_secrets(
            NextToken=next_token,
        )
    else:
        response = client.list_secrets()
    return response


def generate_client(account, role, token):
    if not all([account, role]):
        click.echo("default to current account and assumed role")
        client = boto3.client('secretsmanager')
    else:
        assume_role_session = create_assume_role_session(
            account,
            role,
            _get_arg(token, 'MFA Token', ' ')
        )

        client = assume_role_session.client('secretsmanager')
    return client


def _get_arg(arg, message, defaultv):
    """Prompt the user for input if we don't have them over STDERR so that it works in $()"""
    if not arg:
        return click.prompt(message, default=defaultv)


# todo ove this outside the command so it can be imported by any other commands
def create_assume_role_session(account, role, token):
    aws_profile = os.environ.get("AWS_PROFILE", "default")
    aws_region = os.environ.get("AWS_REGION", "eu-west-1")
    session = boto3.Session(profile_name=aws_profile)

    if account not in config.NEO_ACCOUNTS:
        click.echo(f"Error: Missing account id on config", err=True)
        exit(1)

    # Try to use account_id, else default to argument value
    account_id = config.NEO_ACCOUNTS[account].get("account_id")
    # Try to use available_roles[role] else use argument value
    role_name = config.NEO_ACCOUNTS[account].get("available_roles", {}).get(role, role)

    role_arn = "arn:aws:iam::{account_id}:role/{role}".format(account_id=account_id, role=role_name)
    session_name = ("%s_neotk_assume_%s" % (getuser(), str(uuid1())))[:64]

    click.echo(f"# Assuming {role_arn}", err=True)

    assume_args = {
        "RoleArn": role_arn,
        "RoleSessionName": session_name,
        "DurationSeconds": 900,
    }

    sts = session.client("sts")

    try:
        username = sts.get_caller_identity().get("Arn", "").split("/")[-1]

        if not username:
            click.echo("# Error getting identity", err=True)
            exit(1)

        click.echo(f"# Getting identity for {username}")

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

    return boto3.Session(
        aws_access_key_id=tokens["Credentials"]["AccessKeyId"],
        aws_secret_access_key=tokens["Credentials"]["SecretAccessKey"],
        aws_session_token=tokens["Credentials"]["SessionToken"],
        region_name=aws_region,
    )
