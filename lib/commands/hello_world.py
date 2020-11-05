"""Hello world for Neo Toolkit"""
# See docs/extending.md for more information.

import click
from lib import config, helpers  # pylint: disable=no-name-in-module


@click.command()
def handle():
    """Template for new commands"""
    click.echo("Hello World!")
    print(helpers.get_username())
    print(helpers.str_to_seconds("3600"))
    assert config
