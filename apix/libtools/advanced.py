# -*- encoding: utf-8 -*-
"""This module provides the capability to create an advanced interaction library."""
import attr
import builtins
from pathlib import Path
from logzero import logger
from apix.helpers import merge_dicts, shift_text


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
    def get_field_type(params):
        """ there are a number of cases that aren't explicitly covered here.
        In that case, we just give it a string and see what happens.
        I've currently not deternined a time to use FloatField."""
        params = params.lower()
        name = [piece.strip() for piece in params.split("~")][0]
        if name[-3:] == "_id":
            return "entity"
        if name[-4:] == "_ids":
            return "entities"
        if "mail" in params:
            return "email"
        if "_date" in params:
            return "date"
        if "mask" in name:
            return "netmask"
        if "mac" in params:
            return "mac"
        if "url" in name:
            return "url"
        if "boolean" in params or "true, false" in params:
            return "boolean"
        if "array" in params:
            return [EntityMaker.get_field_type(params.replace("array", ""))]
        if "datetime" in params:
            return "datetime"
        if "hash" in params:
            return {}
        if "number" in params or "integer" in params:
            return "integer"
        return "alpha"

    @staticmethod
    def format_parameter(param_string):
        """Take in a parameter string and return one that matches our template

        Example: cname  ~ required ~ Must be ... string from 1 to 128 characters
        Output: {"cname": {"required": True, "type": "alpha#15"}
        """
        name, required, specs = [_.strip() for _ in param_string.split("~")]
        required = required == "required"
        ptype = EntityMaker.get_field_type(specs)
        if " characters " in param_string:
            split_param = param_string.split()
            try:
                max_len = int(split_param[split_param.index("characters") - 1])
                max_len = int(max_len / 2)  # let's not get too crazy
            except ValueError:
                logger.warning(
                    f"Unable to determine max length for {param_string}. Using 15."
                )
                max_len = 15  # if it isn't where expected, then assign a sane value
            ptype = f"{ptype}#{max_len}"
        return {name: {"required": required, "type": ptype}}

    @staticmethod
    def make_dict(name_list, required, specs):
        """Turn a list of names (with require/spec fields) into a nested dictionary

        Level1[Level2][Level3] ~ optional ~ must be a string

        Returns: {"Level1": {"Level2": {"Level3": {"required": False, "type": "alpha"}}}}
        """
        if len(name_list) > 1:
            return {name_list[0]: EntityMaker.make_dict(name_list[1:], required, specs)}
        else:
            return EntityMaker.format_parameter(
                f"{name_list[0]} ~ {required} ~ {specs}"
            )

    @staticmethod
    def compile_params(param_list):
        """Take a list of params and compile them into a dictionary

        - compute_resource  ~ required ~ Must be a Hash
        - compute_resource[name]  ~ optional ~ Must be a String
        - compute_resource[provider]  ~ optional ~ Must be a String

        returns: {"compute_resource": "required": True, "type" {
            "name": {"required": False, "type: "alpha"},
            "provider" {"required": False, "type": "alpha"},
        }}
        """
        compiled_params = {}
        for param in param_list:
            name, *required, specs = [_.strip() for _ in param.split("~")]
            if not required:
                logger.warning(f"Expected parameter for required in: {param}")
                required = ["optional"]
            required = required[0]
            name_list = [_.replace("]", "") for _ in name.split("[")]
            comped = EntityMaker.make_dict(name_list, required, specs)
            compiled_params = merge_dicts(compiled_params, comped)
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
        ent_temp_f = Path("libs/templates/advanced/method.template")
        if not ent_temp_f.exists():
            logger.error(f"Unable to find {ent_temp_f.absolute()}.")
            return
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
                    "~~param_dict~~", str(self.compile_params(contents["parameters"]))
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
        ent_temp_f = Path("libs/templates/advanced/class.template")
        if not ent_temp_f.exists():
            logger.error(f"Unable to find {ent_temp_f.absolute()}.")
            return
        loaded_t = None
        with ent_temp_f.open("r+") as f_load:
            loaded_t = f_load.read()

        # fill the template
        loaded_t = loaded_t.replace("~~FeatureName~~", class_name)
        loaded_t = loaded_t.replace(
            "~~ProductName~~", self.name_to_class(self.api_name)
        )
        loaded_t = loaded_t.replace(
            "~~class methods~~",
            shift_text(
                self.fill_method_template(class_name, self.api_dict[entity]["methods"])
            ),
        )
        return loaded_t

    def create_entities_file(self):
        """Populate an entities.py with filled entity templates"""
        logger.debug(f"Creating {self.api_name}.py file.")
        all_entity_templates = "".join(
            [self.fill_entity_template(entity) for entity in self.api_dict]
        )

        entities_file = Path("libs/templates/advanced/advanced.template")
        if not entities_file.exists():
            logger.error(f"Unable to find {entities_file}.")
            return
        loaded_ent_f = None
        with entities_file.open("r+") as ent_file:
            loaded_ent_f = ent_file.read()
        loaded_ent_f = loaded_ent_f.replace(
            "~~ProductName~~", self.name_to_class(self.api_name)
        )
        loaded_ent_f = loaded_ent_f.replace("~~feature classes~~", all_entity_templates)

        save_file = Path(
            f"libs/generated/advanced/{self.api_version}/{self.api_name}.py"
        )
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
class AdvancedMaker:
    api_dict = attr.ib(repr=False)
    api_name = attr.ib()
    api_version = attr.ib()

    def make(self):
        """Make all the changes needed to create the advanced library version"""
        entity_maker = EntityMaker(self.api_dict, self.api_name, self.api_version)
        entity_maker.create_entities_file()
