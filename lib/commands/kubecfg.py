"""Fetch the configuration for kubecfg"""

import subprocess

import click

from neotklib import config  # pylint: disable=no-name-in-module


@click.command()
@click.argument("account", type=click.Choice(config.NEO_ACCOUNTS.keys()))
@click.argument("cluster", required=False)
def handle(account, cluster):
    """Fetch the configuration for kubecfg"""
    if not cluster:
        cluster = click.prompt(
            "Cluster",
            type=click.Choice(config.NEO_ACCOUNTS[account].get("kubecfg", {}).keys()),
        )

    cluster = config.NEO_ACCOUNTS[account]["kubecfg"][cluster]

    if "alias" in cluster:
        subprocess.call(
            f"aws eks update-kubeconfig --name {cluster['cluster']} --alias {cluster['alias']}",
            shell=True,
        )
    elif "bucket" in cluster:
        subprocess.call(
            f"kops export --name {cluster['cluster']} --state s3://{cluster['bucket']} kubecfg",
            shell=True,
        )
w
