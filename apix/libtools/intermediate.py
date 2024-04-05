"""This module provides the capability to create an intermediate interaction library."""
import builtins
from pathlib import Path

import attr
from logzero import logger

from apix.helpers import shift_text


@attr.s()
class EntityMaker:
    api_dict = attr.ib(repr=False)
    api_name = attr.ib()
    api_version = attr.ib()

    @staticmethod
    def name_to_class(entity_name):
        """Convert an entity name to a class name. ent_name => EntName"""
        if entity_name[-1] == "s":  # we don't want pluralized names
            entity_name = entity_name[:-1]
        return "".join(x.capitalize() for x in entity_name.split("_"))

    @staticmethod
    def fix_name(name):
        """Determine if the name is reserved and adjust if needed"""
        if name in dir(builtins) or name in ["import"]:
            logger.warning(f"{name} is a python builtin, changing to {name}_")
            name = f"{name}_"
        return name

    @staticmethod
    def compile_params(param_list):
        """Take a list of params and compile them into a list
        nested parameters are beyond the scope of this template


        - id ~ required ~ Must be an integer
        - compute_resource  ~ required ~ Must be a Hash
        - compute_resource[name]  ~ optional ~ Must be a String

        returns: ["id", "compute_resource"]
        """
        compiled_params = []
        for param in param_list:
            name, *_ = (_.strip() for _ in param.split("~"))
            if "[" not in name:
                compiled_params.append(name)
        return compiled_params

    @staticmethod
    def compile_paths(path_list):
        """Take in a list of paths and format them appropriately

        - PUT /api/compute_resources/:compute_resource_id/compute_attributes/:id
        - PUT /api/compute_profiles/:compute_profile_id/compute_attributes/:id
        - PUT /api/compute_attributes/:id

        returns: [
            ("PUT", "/api/compute_resources/{compute_resource_id}/compute_attributes/{id}"),
            ("PUT", "/api/compute_profiles/{compute_profile_id}/compute_attributes/{id}"),
            ("PUT", "/api/compute_attributes/{id}"),
        ]
        """
        compiled_paths = []
        for path in path_list:
            method, path_str = path.split()
            path_decomp = path_str.split("/")
            path_recomp = ""
            for p_slice in path_decomp:
                if p_slice.startswith(":"):
                    path_recomp = f"{path_recomp}/{{{p_slice[1:]}}}"
                elif p_slice:
                    path_recomp = f"{path_recomp}/{p_slice}"
            compiled_paths.append((method, path_recomp))
        return compiled_paths

    # @staticmethod
    # def arg_override(entity_name, field_entity):
    #     """In some parts of Sat6's API some params refer to another entity"""
    #     if field_entity == "Environment":
    #         if entity_name not in ["ContentViewVersion", "Location", "Organization"]:
    #             field_entity = "LifecycleEnvironment"
    #     return field_entity

    def fill_method_template(self, class_name, methods):
        """Load and fill out a method template for every method"""
        logger.debug(f"Filling template for {class_name}'s methods.")
        # load the template
        ent_temp_f = Path("libs/templates/intermediate/method.template")
        if not ent_temp_f.exists():
            logger.error(f"Unable to find {ent_temp_f.absolute()}.")
            return None
        loaded_template = None
        with ent_temp_f.open("r+") as f_load:
            loaded_template = f_load.read()

        # fill the template for each method
        compiled_template = ""
        for method in methods:
            for method_name, contents in method.items():
                temp_late = loaded_template  # hahaha get it?!
                temp_late = temp_late.replace("~~method_name~~", self.fix_name(method_name))
                temp_late = temp_late.replace(
                    "~~param_list~~", str(self.compile_params(contents["parameters"]))
                )
                temp_late = temp_late.replace(
                    "~~path_list~~", str(self.compile_paths(contents["paths"]))
                )
                compiled_template += temp_late
        return compiled_template

    def fill_entity_template(self, entity):
        """Fill out and return an entity template, based on `entity`"""
        # get all variables
        class_name = self.name_to_class(entity)
        # load the template
        ent_temp_f = Path("libs/templates/intermediate/class.template")
        if not ent_temp_f.exists():
            logger.error(f"Unable to find {ent_temp_f.absolute()}.")
            return None
        loaded_t = None
        with ent_temp_f.open("r+") as f_load:
            loaded_t = f_load.read()

        # fill the template
        loaded_t = loaded_t.replace("~~FeatureName~~", class_name)
        loaded_t = loaded_t.replace("~~ProductName~~", self.name_to_class(self.api_name))
        return loaded_t.replace(
            "~~class methods~~",
            shift_text(self.fill_method_template(class_name, self.api_dict[entity]["methods"])),
        )

    def create_entities_file(self):
        """Populate an entities.py with filled entity templates"""
        logger.debug(f"Creating {self.api_name}.py file.")
        all_entity_templates = "".join(
            [self.fill_entity_template(entity) for entity in self.api_dict]
        )

        entities_file = Path("libs/templates/intermediate/intermediate.template")
        if not entities_file.exists():
            logger.error(f"Unable to find {entities_file}.")
            return
        loaded_ent_f = None
        with entities_file.open("r+") as ent_file:
            loaded_ent_f = ent_file.read()
        loaded_ent_f = loaded_ent_f.replace("~~ProductName~~", self.name_to_class(self.api_name))
        loaded_ent_f = loaded_ent_f.replace("~~feature classes~~", all_entity_templates)

        save_file = Path(f"libs/generated/intermediate/{self.api_version}/{self.api_name}.py")
        if save_file.exists():
            logger.warning(f"Overwriting {save_file}")
            save_file.unlink()
        # create the directory, if it doesn't exist
        save_file.parent.mkdir(parents=True, exist_ok=True)
        save_file.touch()
        logger.info(f"Saving results to {save_file}")
        with save_file.open("w+") as outfile:
            outfile.write(loaded_ent_f)
        logger.info(f"It is recommended to run `black {save_file}`")


@attr.s()
class IntermediateMaker:
    api_dict = attr.ib(repr=False)
    api_name = attr.ib()
    api_version = attr.ib()

    def make(self):
        """Make all the changes needed to create the intermediate library version"""
        entity_maker = EntityMaker(self.api_dict, self.api_name, self.api_version)
        entity_maker.create_entities_file()
