"""This module provides the capability to create a new nailgun version."""

from logzero import logger

from apix import helpers
from apix.libtools import advanced, basic, intermediate, nailgun, typed

TEMPLATE_MAKERS = {
    "typed": typed.TypedMaker,
    "advanced": advanced.AdvancedMaker,
    "basic": basic.BasicMaker,
    "intermediate": intermediate.IntermediateMaker,
    "nailgun": nailgun.NailgunMaker,
}


class LibMaker:
    def __init__(self, api_name=None, api_version=None, template_name=None, data_dir=None):
        self.api_name = api_name
        self.api_version = api_version
        self.template_name = template_name
        self.data_dir = data_dir
        self.__attrs_post_init__()

    def __attrs_post_init__(self):
        if not self.api_name:
            apis = helpers.get_api_list(data_dir=self.data_dir)
            if apis:
                self.api_name = apis[0]
            else:
                logger.warning("No known APIs found! Try exploring.")
                return

        if not self.api_version:
            self.api_version = helpers.get_latest(self.api_name, data_dir=self.data_dir)

    def make_lib(self):
        TemplateMaker = TEMPLATE_MAKERS.get(self.template_name.lower())
        if not TemplateMaker:
            logger.warning(f"I don't know how to make a library for {self.api_name}")
            return
        logger.info(f"Making a {self.template_name} library for {self.api_version}")
        api_dict = helpers.load_api(self.api_name, self.api_version, data_dir=self.data_dir)
        lib_maker = TemplateMaker(
            api_dict=api_dict, api_name=self.api_name, api_version=self.api_version
        )
        lib_maker.make()
