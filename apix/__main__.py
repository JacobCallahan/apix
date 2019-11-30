# -*- encoding: utf-8 -*-
"""Main module for rizza's interface."""
import argparse
import pytest
import sys
from apix.explore import AsyncExplorer
from apix.diff import VersionDiff
from apix.libtools.libmaker import LibMaker
from apix.helpers import get_api_list, get_ver_list, LooseVersion
from apix import logger


class Main(object):
    """This main class will allow for better nested arguments (git stlye)"""

    def __init__(self):
        # self.conf = Config()
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "action",
            type=str,
            choices=["explore", "diff", "makelib", "list", "test"],
            help="The action to perform.",
        )
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.action):
            logger.warning(f"Action {args.action} is not supported.")
            parser.print_help()
            exit(1)
        getattr(self, args.action)()

    def explore(self):
        """Explore a target API and export the findings"""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-n",
            "--api-name",
            type=str,
            required=True,
            help="The name of the API (satellite6).",
        )
        parser.add_argument(
            "-u",
            "--host-url",
            type=str,
            required=True,
            help="The url for the API's host (http://my.host.domain/).",
        )
        parser.add_argument(
            "-b",
            "--base-path",
            type=str,
            default="apidoc/",
            help="The apidoc location relative to the host's url (apidoc/).",
        )
        parser.add_argument(
            "-v",
            "--version",
            type=str,
            default=None,
            help="The API version we're exploring (6.3).",
        )
        parser.add_argument(
            "-p",
            "--parser",
            type=str,
            default="apipie",
            help="The name of the parser to use when pulling data (apipie).",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default="./",
            help="The base directory in which to save exports.",
        )
        parser.add_argument(
            "--compact",
            action="store_true",
            help="Strip all the extra information from the saved data.",
        )
        parser.add_argument(
            "--debug", action="store_true", help="Enable debug loggin level."
        )

        args = parser.parse_args(sys.argv[2:])
        if args.debug:
            logger.setup_logzero(level="debug")
        try:
            LooseVersion(args.version)
        except ValueError as err:
            logger.error(err)
            sys.exit(1)
        explorer = AsyncExplorer(
            name=args.api_name,
            version=args.version,
            host_url=args.host_url,
            base_path=args.base_path,
            parser=args.parser,
            data_dir=args.data_dir,
            compact=args.compact,
        )
        explorer.explore()
        explorer.save_data()
        sys.exit(0)

    def diff(self):
        """Determine the changes between two API versions"""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-n",
            "--api-name",
            type=str,
            default=None,
            help="The name of the API (satellite6).",
        )
        parser.add_argument(
            "-l",
            "--latest-version",
            type=str,
            default=None,
            help="The latest version of the API",
        )
        parser.add_argument(
            "-p",
            "--previous-version",
            type=str,
            default=None,
            help="A previous version of the API",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default="./",
            help="The base directory in which to save diffs.",
        )
        parser.add_argument(
            "--compact",
            action="store_true",
            help="Strip all the extra information from the diff.",
        )
        parser.add_argument(
            "--debug", action="store_true", help="Enable debug loggin level."
        )

        args = parser.parse_args(sys.argv[2:])
        if args.debug:
            logger.setup_logzero(level="debug")
        vdiff = VersionDiff(
            api_name=args.api_name,
            ver1=args.latest_version,
            ver2=args.previous_version,
            data_dir=args.data_dir,
            compact=args.compact,
        )
        vdiff.diff()
        vdiff.save_diff()
        sys.exit(0)

    def makelib(self):
        """Create a library to interact with a specific API version"""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-n",
            "--api-name",
            type=str,
            default=None,
            help="The name of the API (satellite6).",
        )
        parser.add_argument(
            "-v",
            "--version",
            type=str,
            default=None,
            help="The API version we're creating a library for (6.3).",
        )
        parser.add_argument(
            "-t",
            "--template",
            type=str,
            default="advanced",
            help="The template to base your library on.",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default="./",
            help="The base directory in which to save libraries.",
        )
        parser.add_argument(
            "--debug", action="store_true", help="Enable debug loggin level."
        )

        args = parser.parse_args(sys.argv[2:])
        if args.debug:
            logger.setup_logzero(level="debug")
        libmaker = LibMaker(
            api_name=args.api_name,
            api_version=args.version,
            template_name=args.template,
            data_dir=args.data_dir,
        )
        libmaker.make_lib()
        sys.exit(0)

    def list(self):
        """List out the API information we have stored"""
        parser = argparse.ArgumentParser()
        parser.add_argument("subject", type=str, choices=["apis", "versions"])
        parser.add_argument(
            "-n",
            "--api-name",
            type=str,
            default=None,
            help="The name of the api you want to list versions of.",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default="./",
            help="The base directory in which to search for stored exports.",
        )

        args = parser.parse_args(sys.argv[2:])

        if args.subject == "apis":
            api_list = get_api_list(args.data_dir)
            if api_list:
                print("\n".join(api_list))
            else:
                print(f"Unable to find saved APIs in {args.data_dir}")
        elif args.subject == "versions" and args.api_name:
            ver_list = get_ver_list(args.api_name, args.data_dir)
            if ver_list:
                print("\n".join(ver_list))
            else:
                print(f"Unable to find saved versions in {args.data_dir}")
        sys.exit(0)

    def test(self):
        """List out some information about our entities and inputs."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--args",
            type=str,
            nargs="+",
            help='pytest args to pass in. (--args="-r a")',
        )
        args = parser.parse_args(sys.argv[2:])
        if args.args:
            pyargs = args.args
        else:
            pyargs = ["-q"]
        pytest.cmdline.main(args=pyargs)
        sys.exit(0)

    def __repr__(self):
        return None


if __name__ == "__main__":
    Main()
