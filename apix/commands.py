"""Main module for apix's interface."""
from rich import print
from rich.table import Table
import rich_click as click

from apix import helpers, logger
from apix.diff import VersionDiff
from apix.explore import AsyncExplorer
from apix.libtools.libmaker import LibMaker


def _version():
    import pkg_resources

    return pkg_resources.get_distribution("apix").version


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
    default="info",
    help="The log level to use.",
    callback=lambda ctx, param, value: logger.setup_logzero(value),
    is_eager=True,
    expose_value=False,
)
@click.version_option(version=_version())
def cli():
    """Main entry point for the CLI."""
    pass


@cli.command()
@click.option(
    "-n",
    "--api-name",
    type=str,
    required=True,
    help="The name of the API (satellite).",
)
@click.option(
    "-u",
    "--host-url",
    type=str,
    required=True,
    help="The url for the API's host (http://my.host.domain/).",
)
@click.option(
    "-b",
    "--base-path",
    type=str,
    default="apidoc/",
    help="The apidoc location relative to the host's url (apidoc/).",
)
@click.option(
    "-v",
    "--version",
    type=str,
    default=None,
    help="The API version we're exploring (6.3).",
)
@click.option(
    "-p",
    "--parser",
    type=str,
    default="apipie",
    help="The name of the parser to use when pulling data (apipie).",
)
@click.option(
    "--data-dir",
    type=str,
    default="./",
    help="The base directory in which to save exports.",
)
@click.option(
    "--compact",
    is_flag=True,
    help="Strip all the extra information from the saved data.",
)
# (too-many-arguments)
def explore(api_name, host_url, base_path, version, parser, data_dir, compact):
    """Explore a target API and export the findings"""
    explorer = AsyncExplorer(
        name=api_name,
        version=version,
        host_url=host_url,
        base_path=base_path,
        parser=parser,
        data_dir=data_dir,
        compact=compact,
    )
    explorer.explore()
    explorer.save_data()


@cli.command()
@click.option(
    "-n",
    "--api-name",
    type=str,
    default=None,
    help="The name of the API (satellite6).",
)
@click.option(
    "-l",
    "--latest-version",
    type=str,
    default=None,
    help="The latest version of the API",
)
@click.option(
    "-p",
    "--previous-version",
    type=str,
    default=None,
    help="A previous version of the API",
)
@click.option(
    "--data-dir",
    type=str,
    default="./",
    help="The base directory in which to save diffs.",
)
@click.option(
    "--compact",
    is_flag=True,
    help="Strip all the extra information from the saved data.",
)
def diff(api_name, latest_version, previous_version, data_dir, compact):
    """Determine the changes between two API versions"""
    vdiff = VersionDiff(
        api_name=api_name,
        ver1=latest_version,
        ver2=previous_version,
        data_dir=data_dir,
        compact=compact,
    )
    vdiff.diff()
    vdiff.save_diff()


@cli.command()
@click.option(
    "-n",
    "--api-name",
    type=str,
    default=None,
    help="The name of the API (satellite6).",
)
@click.option(
    "-v",
    "--version",
    type=str,
    default=None,
    help="The API version we're creating a library for (6.3).",
)
@click.option(
    "--data-dir",
    type=str,
    default="./",
    help="The base directory in which to save libraries.",
)
def compact(api_name, version, data_dir):
    """Make a compact version of the API data"""
    # load the api data
    api_data = helpers.load_api(api_name, version, data_dir)
    # compact the loaded data
    api_data = VersionDiff._truncate(api_data)
    # save the compacted data
    helpers.save_api(api_name, version, api_data, data_dir, True)


@cli.command()
@click.option(
    "-n",
    "--api-name",
    type=str,
    default=None,
    help="The name of the API (satellite6).",
)
@click.option(
    "-v",
    "--version",
    type=str,
    default=None,
    help="The API version we're creating a library for (6.3).",
)
@click.option(
    "-t",
    "--template",
    type=str,
    default="advanced",
    help="The template to base your library on.",
)
@click.option(
    "--data-dir",
    type=str,
    default="./",
    help="The base directory in which to save libraries.",
)
def makelib(api_name, version, template, data_dir):
    """Create a library to interact with a specific API version"""
    libmaker = LibMaker(
        api_name=api_name,
        api_version=version,
        template_name=template,
        data_dir=data_dir,
    )
    libmaker.make_lib()


@cli.command()
@click.argument("subject", type=click.Choice(["apis", "versions"]))
@click.option(
    "-n",
    "--api-name",
    type=str,
    default=None,
    help="The name of the API (satellite6).",
)
@click.option(
    "--data-dir",
    type=str,
    default="./",
    help="The base directory in which to save libraries.",
)
def list(subject, api_name, data_dir):
    """List out the API information we have stored"""
    if subject == "apis":
        api_list = helpers.get_api_list(data_dir)
        if api_list:
            table = Table(title="Available APIs")
            table.add_column("API Name", style="cyan")
            for api in api_list:
                table.add_row(api)
            print(table)
        else:
            print(f"Unable to find saved APIs in {data_dir}")
    elif subject == "versions" and api_name:
        ver_list = helpers.get_ver_list(api_name, data_dir)
        if ver_list:
            table = Table(title=f"Available Versions for {api_name}")
            table.add_column("Version", style="cyan")
            for ver in ver_list:
                table.add_row(ver)
            print(table)
        else:
            print(f"Unable to find saved versions for {api_name} in {data_dir}")


if __name__ == "__main__":
    cli()
