# -*- encoding: utf-8 -*-
"""
Provides a class with methods that parse the api correctly.

Parser classes must currently implement the following methods:
    pull_links - Returns a list of links to visit from the API's base url.
    yaml_format - Returns yaml-friendly dict of the compiled data.
    scrape_content - Returns a dict of params and paths from a single page.
"""
import attr
from logzero import logger


@attr.s()
class APIPie:
    """Parser class for Ruby's APIPie apidoc generator"""

    _data = attr.ib(default=attr.Factory(dict), repr=False)
    params = attr.ib(default=attr.Factory(dict), repr=False)

    @staticmethod
    def _compile_method(method_dict):
        """form the parameters and paths lists"""
        params = [
            f'{param["name"]} ~ {"required" if param["required"] else "optional"} ~ {param["expected_type"]}'
            for param in method_dict["params"]
        ]
        paths = [
            f'{path["http_method"].upper()} {path["api_url"]}'
            for path in method_dict["apis"]
        ]
        return {"paths": paths, "params": params}

    def scrape_content(self, result):
        """Compile the data into their corresponding classifications"""
        entity_docs = result.json()["docs"]["resources"]
        for name, data in entity_docs.items():
            logger.debug(f"Compiling {name} with {len(data['methods'])} methods")
            self._data[name] = {"methods": []}
            for method in data["methods"]:
                self._data[name]["methods"].append(
                    {method["name"]: self._compile_method(method)}
                )
                self.params.update(
                    {param["name"]: param for param in method["params"]}
                )

    def yaml_format(self, ingore=None):
        """Return the compiled data in a yaml-friendly format"""
        return self._data
