"""
Provides a class with methods that parse the api correctly.

Parser classes must currently implement the following methods:
    pull_links - Returns a list of links to visit from the API's base url.
    yaml_format - Returns yaml-friendly dict of the compiled data.
    scrape_content - Returns a dict of params and paths from a single page.
"""
from logzero import logger

from apix.helpers import clean_string


class APIPie:
    """Parser class for Ruby's APIPie apidoc generator"""

    def __init__(self):
        self._data = {}
        self.params = {}

    @staticmethod
    def _compile_params(params, parent=None):
        """Compile the params into a list of strings"""
        compiled = []
        for param in params:
            status = "optional"
            if param["deprecated"]:
                status = "deprecated"
            elif param["required"]:
                status = "required"
            if parent:
                param["name"] = f"{parent}[{param['name']}]"
            compiled.append(
                f'{param["name"]} ~ {status} ~ {clean_string(param["validator"]).lower()}'
            )
            # some params have nested parameters, so we recurse to get them
            if param.get("params"):
                compiled.extend(APIPie._compile_params(param["params"], parent=param["name"]))
        return compiled

    @staticmethod
    def _compile_method(method_dict):
        """form the parameters and paths lists"""
        paths = [
            f'{path["http_method"].upper()} {path["api_url"]}' for path in method_dict["apis"]
        ]
        return {"paths": paths, "params": APIPie._compile_params(method_dict["params"])}

    def scrape_content(self, result):
        """Compile the data into their corresponding classifications"""
        entity_docs = result.json()["docs"]["resources"]
        for name, data in entity_docs.items():
            logger.debug(f"Compiling {name} with {len(data['methods'])} methods")
            self._data[name] = {"methods": []}
            for method in data["methods"]:
                self._data[name]["methods"].append({method["name"]: self._compile_method(method)})
                self.params.update({param["name"]: param for param in method["params"]})

    def yaml_format(self, ingore=None):
        """Return the compiled data in a yaml-friendly format"""
        return self._data
