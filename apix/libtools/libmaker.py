# -*- encoding: utf-8 -*-
"""This module provides the capability to create a new nailgun version."""
import attr
from pathlib import Path
from logzero import logger
from apix import helpers
from apix.libtools import nailgun


@attr.s()
class LibMaker():
    api_name = attr.ib(default=None)
    api_version = attr.ib(default=None)

    def __attrs_post_init__(self):
        if not self.api_name:
            apis = helpers.get_api_list()
            if apis:
                self.api_name = apis[0]
            else:
                logger.warning('No known APIs found! Try exploring.')
                return

        if not self.api_version:
            self.api_version = helpers.get_latest(self.api_name)

    def make_lib(self):
        if self.api_name.lower() == 'satellite6':
            logger.info(
                f'Making a nailgun library for {self.api_version}'
                ' at libs/generated/nailgun/'
            )
            api_dict = helpers.load_api(self.api_name, self.api_version)
            nailgun_maker = nailgun.NailgunMaker(
                api_dict = api_dict,
                api_name = self.api_name,
                api_version = self.api_version
            )
            nailgun_maker.make()
        else:
            logger.warning(
                f"I don't know how to make a library for {self.api_name}")
