# -*- encoding: utf-8 -*-
"""Main module for rizza's interface."""
import argparse
import pytest
import sys
from apix.explore import AsyncExplorer
from apix.diff import VersionDiff
from apix.helpers import get_api_list, get_ver_list
from apix import logger


class Main(object):
    """This main class will allow for better nested arguments (git stlye)"""
    def __init__(self):
        # self.conf = Config()
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "action", type=str, choices=['explore', 'diff', 'list'],
            help="The action to perform.")
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.action):
            # logger.warning('Action {0} is not supported.'.format(args.action))
            parser.print_help()
            exit(1)
        getattr(self, args.action)()

    def explore(self):
        """Explore a target API and export the findings"""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-n", "--api-name", type=str, required=True,
            help="The name of the API (satellite6).")
        parser.add_argument(
            "-u", "--host-url", type=str, required=True,
            help="The url for the API's host (http://my.host.domain/).")
        parser.add_argument(
            "-b", "--base-path", type=str, default='apidoc/',
            help="The apidoc location relative to the host's url (apidoc/).")
        parser.add_argument(
            "-v", "--version", type=str, default=None,
            help="The API version we're exploring (6.3).")
        parser.add_argument(
            "--debug", action="store_true",
            help="Enable debug loggin level.")

        args = parser.parse_args(sys.argv[2:])
        if args.debug:
            logger.setup_logzero(level='debug')
        explorer = AsyncExplorer(
            name=args.api_name,
            version=args.version,
            host_url=args.host_url,
            base_path=args.base_path
        )
        explorer.explore()
        explorer.save_data()

    def diff(self):
        """Determine the changes between two API versions"""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-n", "--api-name", type=str, required=True,
            help="The name of the API (satellite6).")
        parser.add_argument(
            "-l", "--latest-version", type=str, default=None,
            help="The latest version of the API")
        parser.add_argument(
            "-p", "--previous-version", type=str, default=None,
            help="A previous version of the API")
        parser.add_argument(
            "--debug", action="store_true",
            help="Enable debug loggin level.")

        args = parser.parse_args(sys.argv[2:])
        if args.debug:
            logger.setup_logzero(level='debug')
        vdiff = VersionDiff(
            api_name=args.api_name,
            ver1=args.latest_version,
            ver2=args.previous_version,
        )
        vdiff.diff()
        vdiff.save_diff()

    def list(self):
        """List out the API information we have stored"""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "subject", type=str,
            choices=['apis', 'versions'])
        parser.add_argument(
            "-n", "--api-name", type=str, default=None,
            help="The name of the api you want to list versions of.")

        args = parser.parse_args(sys.argv[2:])

        if args.subject == 'apis':
            print("\n".join(get_api_list()))
        elif args.subject == 'versions' and args.api_name:
            print("\n".join(get_ver_list(args.api_name)))

    def test(self):
        """List out some information about our entities and inputs."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--args", type=str, nargs='+',
            help='pytest args to pass in. (--args="-r a")')
        args = parser.parse_args(sys.argv[2:])
        if args.args:
            pyargs = args.args
        else:
            pyargs=['-q']
        pytest.cmdline.main(args=pyargs)

    def __repr__(self):
        return None

if __name__ == '__main__':
    Main()
