import builtins
import keyword
from pathlib import Path
import re
import subprocess

from logzero import logger
import yaml

from apix.helpers import shift_text

# Track all fauxfactory types we encounter and need to generate
FF_TYPES = set()


class TemplateManager:
    """Handles template loading and manipulation operations"""

    @staticmethod
    def load_template(template_name):
        """Load a template file and return its content"""
        template_path = Path(f"libs/templates/typed/{template_name}.template")
        if not template_path.exists():
            logger.error(f"Unable to find template: {template_path.absolute()}")
            return ""

        return template_path.read_text()

    @staticmethod
    def replace_placeholders(template, replacements):
        """Replace all placeholders in a template with their values"""
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(f"~~{placeholder}~~", value)
        return result


class CustomEntityMaker:
    def __init__(
        self,
        api_dict,
        api_name,
        api_version,
        ff_types=None,
        template_manager=None,
        special_mappings=None,
    ):
        self.api_dict = api_dict
        self.api_name = api_name
        self.api_version = api_version
        self.ff_types = ff_types if ff_types is not None else set()
        self.template_manager = (
            template_manager if template_manager is not None else TemplateManager()
        )
        self.special_mappings = special_mappings if special_mappings is not None else {}
        self.__attrs_post_init__()

    def __attrs_post_init__(self):
        """Load special mappings from YAML file after initialization"""
        self.special_mappings = self._load_special_mappings()

    def _load_special_mappings(self):
        """Load special entity mappings from a YAML file based on the API name"""
        # Get the current file's directory
        current_dir = Path(__file__).parent

        # Try to find a <product_name>.yaml file
        product_yaml = current_dir / f"{self.api_name.lower()}.yaml"

        if not product_yaml.exists():
            logger.debug(f"No special mappings file found at {product_yaml}")
            return {}

        try:
            with product_yaml.open() as f:
                yaml_data = yaml.safe_load(f)

            if not isinstance(yaml_data, dict):
                logger.warning(f"Invalid YAML format in {product_yaml}")
                return {}

            mappings = yaml_data.get("special_mappings", {})
            logger.info(f"Loaded {len(mappings)} special mappings from {product_yaml}")
            return mappings

        except Exception as e:
            logger.error(f"Error loading special mappings from {product_yaml}: {e}")
            return {}

    @staticmethod
    def name_to_class(entity_name):
        """Convert an entity name to a class name. ent_name => EntName"""
        if not entity_name:
            return ""
        if entity_name[-1] == "s" and entity_name[-2:] != "ss":  # Keep "address" as "Address"
            entity_name = entity_name[:-1]
        return "".join(x.capitalize() or "_" for x in entity_name.split("_"))

    @staticmethod
    def fix_name(name):
        """Determine if the name is reserved and adjust if needed"""
        # Check for Python keywords (like 'global', 'class', etc.)
        if keyword.iskeyword(name) or name in dir(builtins) or name in ["import", "type", "id"]:
            original_name = name
            name = f"{name}_"
            logger.debug(
                f"{original_name} is a python keyword/builtin/reserved, changing to {name}"
            )
        return name

    @staticmethod
    def compile_paths(path_list):
        compiled_paths = []
        for path_entry in path_list:
            if isinstance(path_entry, str):  # Original format "METHOD /path"
                method, path_str = path_entry.split(maxsplit=1)
            elif isinstance(path_entry, dict):  # New format {"method": "GET", "path": "/path"}
                method = path_entry.get("method", "GET")
                path_str = path_entry.get("path", "")
            else:
                logger.warning(f"Unknown path format: {path_entry}")
                continue

            path_recomp = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path_str)
            compiled_paths.append((method, path_recomp))
        return compiled_paths

    def _load_template(self, template_name):
        """Load a template file by name"""
        return self.template_manager.load_template(template_name)

    def get_entity_class_name_if_entity(self, param_name):
        """
        Check if the parameter name corresponds to an entity in the API dictionary.
        If so, return the appropriate class name, otherwise return None.
        """
        if not param_name:
            return None

        # Try with singular form (users -> user)
        singular_name = (
            param_name[:-1] if param_name.endswith("s") and param_name[-2:] != "ss" else param_name
        )

        # If either form exists in API dict, convert to class name
        if singular_name in self.api_dict:
            return self.name_to_class(singular_name)
        if param_name in self.api_dict:
            return self.name_to_class(param_name)

        return None

    def _detect_type_patterns(self, spec_lower, param_name):
        """Check for common type patterns in parameter specifications"""
        type_patterns = [
            ("Date", r"\bdate\b", "gen_date"),
            ("DateTime", r"\bdatetime\b", "gen_datetime"),
            ("Time", r"\btime\b", "gen_time"),
            ("Domain", r"\bdomain\b", "gen_domain"),
            ("Email", r"\bemail\b", "gen_email"),
            ("IPAddress", r"\bip\s?addr(?:ess)?\b", "gen_ipaddr"),
            ("MACAddress", r"\bmac\s?addr(?:ess)?\b", "gen_mac"),
            ("URL", r"\burl\b", "gen_url"),
            ("UUID", r"\buuid\b", "gen_uuid"),
        ]

        for type_name, pattern, ff_method in type_patterns:
            if re.search(pattern, spec_lower):
                self.ff_types.add((type_name, ff_method))
                return f"ffTypes.{type_name}"
        return None

    def _detect_special_type(self, param_name):
        if not param_name:
            return None

        param_lower = param_name.lower()
        special_types = [
            ("date", "Date", "gen_date"),
            ("datetime", "DateTime", "gen_datetime"),
            ("time", "Time", "gen_time"),
            ("domain", "Domain", "gen_domain"),
            ("email", "Email", "gen_email"),
            ("ip", "IPAddress", "gen_ipaddr"),
            ("ipaddr", "IPAddress", "gen_ipaddr"),
            ("ip_address", "IPAddress", "gen_ipaddr"),
            ("mac", "MACAddress", "gen_mac"),
            ("mac_address", "MACAddress", "gen_mac"),
            ("netmask", "Netmask", "gen_netmask"),
            ("url", "URL", "gen_url"),
            ("hex", "Hexadecimal", "gen_hexadecimal"),
            ("hexadecimal", "Hexadecimal", "gen_hexadecimal"),
            ("html", "HTML", "gen_html"),
            ("uuid", "UUID", "gen_uuid"),
            ("guid", "UUID", "gen_uuid"),
        ]

        for key, type_name, ff_method in special_types:
            if key in param_lower or param_lower.endswith(f"_{key}"):
                self.ff_types.add((type_name, ff_method))
                return f"ffTypes.{type_name}"
        return None

    def _detect_enum(self, spec_lower):
        enum_match = re.search(r"must be one of: ([^\.]+)", spec_lower)
        if enum_match:
            enum_values = enum_match.group(1).strip()
            if "true" in enum_values and "false" in enum_values:
                return bool
            choices = [choice.strip() for choice in enum_values.split(",")]
            return ("Literal", choices)
        return None

    def _detect_array(self, spec_lower):
        if "array" in spec_lower or "list" in spec_lower:
            array_item_match = re.search(r"array of ([a-zA-Z]+)", spec_lower)
            if array_item_match:
                item_type = array_item_match.group(1).strip()
                if item_type in ("number", "integer"):
                    return list
            return list
        return None

    def get_python_type_from_spec(self, spec_string, param_name):  # noqa: PLR0912
        """Determine Python type from specification string"""
        spec_lower = spec_string.lower()

        # Early return cases
        if "deprecated" in spec_lower:
            logger.debug(f"Parameter {param_name} is deprecated, skipping")
            return None

        # Check if parameter corresponds to an entity
        entity_class = self.get_entity_class_name_if_entity(param_name)
        if entity_class:
            logger.debug(f"Parameter {param_name} matches an entity in the API")
            return entity_class

        # Check for enum types
        enum_type = self._detect_enum(spec_lower)
        if enum_type:
            return enum_type

        # Check for identifier/string type
        if (
            ("must be an identifier" in spec_lower or "string from" in spec_lower)
            and "number" not in spec_lower
            and "integer" not in spec_lower
        ):
            return str

        # Check for array type
        array_type = self._detect_array(spec_lower)
        if array_type:
            return array_type

        # Check for special types based on parameter name
        special_type = self._detect_special_type(param_name)
        if special_type:
            return special_type

        # Check for common data structures
        if "array" in spec_lower or "list" in spec_lower:
            return list
        if "object" in spec_lower or "hash" in spec_lower or "dict" in spec_lower:
            entity = self.get_entity_class_name_if_entity(param_name)
            if entity:
                return entity
            logger.debug(
                "Parameter %s is an object but not an entity: %s",
                param_name,
                spec_string,
            )
            return dict

        # Check for numeric types
        if "number" in spec_lower or "integer" in spec_lower or "numeric" in spec_lower:
            return int

        # Check for boolean
        if "boolean" in spec_lower or "true" in spec_lower or "false" in spec_lower:
            return bool

        # Check for pattern-based types
        pattern_type = self._detect_type_patterns(spec_lower, param_name)
        if pattern_type:
            return pattern_type

        # Check for string types
        if "string" in spec_lower or "char" in spec_lower:
            return str

        # Check for ID fields
        if param_name and (param_name.endswith("_id") or param_name.endswith("_ids")):
            if "number" in spec_lower or "integer" in spec_lower:
                return int
            return str

        # Default to string if no other type identified
        return str

    def _handle_nested_params(
        self, current_level, full_name_str, clean_name_parts, i, req_str, desc_str
    ):
        """Handle nested parameter parsing logic"""
        part_name = clean_name_parts[i]
        is_last_part = i == len(clean_name_parts) - 1
        is_array_item_spec = part_name == "" and not is_last_part

        if is_array_item_spec:
            array_name = clean_name_parts[i - 1]
            children = self._handle_array_item(array_name, current_level, full_name_str)
            if children is None:
                return None
            return children, False

        if is_last_part:
            current_level[part_name] = {
                "name": part_name,
                "required": "required" in req_str.lower(),
                "type_str": self.get_python_type_from_spec(desc_str, part_name),
                "description": desc_str,
                "children": {},
            }
            return current_level, True

        if part_name not in current_level:
            current_level[part_name] = {
                "name": part_name,
                "required": "required" in req_str.lower(),
                "type_str": dict,
                "description": "",
                "children": {},
            }
        type_str = current_level[part_name]["type_str"]
        if isinstance(type_str, type) and type_str is not dict and type_str is not list:
            logger.error(
                "Parameter %s has sub-parameters like %s but was not defined as a dict or list.",
                part_name,
                full_name_str,
            )
            return None, True

        return current_level[part_name]["children"], False

    def _handle_array_item(self, array_name, current_level, full_name_str):
        """Handle array item parameter logic"""
        if array_name not in current_level:
            logger.warning(
                "Array %s not defined before its items. Attempting to create.",
                array_name,
            )
            current_level[array_name] = {
                "name": array_name,
                "required": False,
                "type_str": list,
                "description": "Array of objects",
                "children": {},
            }
        type_str = current_level[array_name]["type_str"]
        if not isinstance(type_str, type) or type_str is not list:
            logger.error(
                "Parameter %s was not defined as an array but sub-parameters like %s exist.",
                array_name,
                full_name_str,
            )
            return None
        return current_level[array_name]["children"]

    def parse_api_parameters(self, api_params_list):
        """Parse API parameters into a structured format"""
        MAX_PARTS = 3
        parsed_params = {}
        if not api_params_list:
            return parsed_params

        for param_entry in api_params_list:
            parts = [p.strip() for p in param_entry.split("~")]
            if len(parts) < MAX_PARTS:
                logger.warning(f"Skipping malformed parameter entry: {param_entry}")
                continue

            full_name_str, req_str, desc_str = parts[0], parts[1], " ".join(parts[2:])

            # Extract name parts from parameter string
            name_parts = re.findall(r"\[([^\]]+)\]|([^\[\]]+)", full_name_str)
            clean_name_parts = []
            for p1, p2 in name_parts:
                if p1:
                    clean_name_parts.append(p1)
                elif p2:
                    clean_name_parts.append(p2.replace("[]", ""))

            current_level = parsed_params

            # Process each part of the parameter name
            for i, _ in enumerate(clean_name_parts):
                result = self._handle_nested_params(
                    current_level, full_name_str, clean_name_parts, i, req_str, desc_str
                )

                if result is None:
                    break

                current_level, done = result
                if done:
                    break

        return parsed_params

    def _infer_list_item_type(self, param_name):  # noqa: PLR0912
        """
        Try to infer the type of items in a list parameter based on naming patterns.
        For parameters ending with _ids, try to match with an entity class.
        Returns tuple (item_type_name, is_id_reference) or None if no match found.
        """
        if not param_name or not param_name.endswith("_ids"):
            return None

        # Extract the potential entity name (remove _ids suffix)
        base_name = param_name[:-4]  # Remove '_ids'

        # Try singular form if it ends with 's' (but not 'ss')
        if base_name.endswith("s") and not base_name.endswith("ss"):
            entity_name = base_name[:-1]
        else:
            entity_name = base_name

        # Try to find entity in special mappings loaded from YAML
        if entity_name in self.special_mappings:
            mapped_name = self.special_mappings[entity_name]
            if mapped_name in self.api_dict:
                logger.debug(f"Mapped {entity_name} to {mapped_name}")
                return (
                    self.name_to_class(
                        mapped_name[:-1] if mapped_name.endswith("s") else mapped_name
                    ),
                    True,
                )

        # Try the special mapping first
        if entity_name in self.special_mappings:
            mapped_name = self.special_mappings[entity_name]
            if mapped_name in self.api_dict:
                logger.debug(f"Mapped {entity_name} to {mapped_name}")
                return (
                    self.name_to_class(
                        mapped_name[:-1] if mapped_name.endswith("s") else mapped_name
                    ),
                    True,
                )

        # Try direct match with API dict keys (singular form)
        if entity_name in self.api_dict:
            return (self.name_to_class(entity_name), True)

        # Try direct match with original base_name
        if base_name in self.api_dict:
            return (self.name_to_class(base_name), True)

        # Try to find a plural form in the API dictionary that matches our singular name
        # This is useful for cases like "host_ids" where we need to map to "hosts"
        for api_key in self.api_dict:
            # Skip keys that don't end with 's'
            if not api_key.endswith("s"):
                continue

            # Get the singular form of the API key
            api_key_singular = api_key[:-1]

            # If our entity name matches the singular API key, use the API key class
            if entity_name == api_key_singular:
                logger.debug(f"Found plural form {api_key} for {entity_name}")
                return (self.name_to_class(api_key_singular), True)

        # Try a more lenient match - check if entity_name is contained in any API key
        # Helps with compound names like "content_view_version" matching "content_view_versions"
        for api_key in self.api_dict:
            if entity_name in api_key:
                logger.debug(f"Found partial match {api_key} for {entity_name}")
                # Get class name from API key but keep it singular
                return (
                    self.name_to_class(api_key[:-1] if api_key.endswith("s") else api_key),
                    True,
                )

        # Finally try the base_name with the same approach
        for api_key in self.api_dict:
            if base_name in api_key:
                logger.debug(f"Found partial match {api_key} for {base_name}")
                # Get class name from API key but keep it singular
                return (
                    self.name_to_class(api_key[:-1] if api_key.endswith("s") else api_key),
                    True,
                )

        # Log at debug level instead of warning since this is expected for some parameters
        logger.debug(f"Could not find entity class for list parameter {param_name}")
        return None

    def get_python_type_annotation(self, param_details, param_name=None):
        """
        Convert parameter details to a Python type annotation string.
        Returns: A string representing the type annotation (e.g., "str", "int | None")
        """
        type_value = param_details["type_str"]
        is_required = param_details["required"]

        # Handle lists with potential entity item types
        if isinstance(type_value, type) and type_value is list and param_name:
            list_item_info = self._infer_list_item_type(param_name)
            if list_item_info:
                entity_class, is_id_ref = list_item_info
                type_str = f"list[{entity_class}.id]" if is_id_ref else f"list[{entity_class}]"
            else:
                type_str = "list"
        # Handle Literal type with enumeration values
        elif isinstance(type_value, tuple) and type_value[0] == "Literal":
            # For Literal type, create a proper Literal annotation
            choices_str = ", ".join([f'"{choice}"' for choice in type_value[1]])
            type_str = f"Literal[{choices_str}]"
        # Handle entity class references
        elif isinstance(type_value, str):
            if type_value[0].isupper():
                # This is a class name reference
                type_str = type_value
            elif type_value in [
                "Date",
                "DateTime",
                "Time",
                "Domain",
                "Email",
                "IPAddress",
                "MACAddress",
                "Netmask",
                "URL",
                "Hexadecimal",
                "HTML",
                "UUID",
            ]:
                # This is a special type that should be referenced through ffTypes
                type_str = f"ffTypes.{type_value}"
            else:
                # This is a built-in type name as string
                type_str = type_value
        else:
            # This is a built-in type
            type_str = type_value.__name__ if type_value else "None"

        # For required parameters, just return the type
        # For optional parameters, return type | None
        return type_str if is_required else f"{type_str} | None = None"

    def generate_typed_parameters_string(self, parsed_params):
        """
        Generates a string representing method parameters with type annotations.
        Excludes 'id' parameter as it will be handled separately.
        """
        if not parsed_params:
            return ""

        required_params, optional_params = [], []
        for name, details in parsed_params.items():
            # Skip 'id' parameter as it will be handled separately
            if name == "id":
                continue

            fixed_name = self.fix_name(name)
            type_annotation = self.get_python_type_annotation(details, param_name=name)
            # Check if parameter has a default value
            if "= None" in type_annotation:
                optional_params.append(f"{fixed_name}: {type_annotation}")
            else:
                required_params.append(f"{fixed_name}: {type_annotation}")

        # Combine parameters with required ones first
        return ", ".join(required_params + optional_params)

    def extract_init_params_from_create_method(self, entity_name, entity_api_data):
        """
        Extract initialization parameters from the entity's create method.
        Look for nested parameters under the entity's name.
        """
        methods_api_data = entity_api_data.get("methods", [])
        create_method_data = None

        # Find the create method data
        if isinstance(methods_api_data, list):
            for method_dict in methods_api_data:
                if isinstance(method_dict, dict) and "create" in method_dict:
                    create_method_data = method_dict["create"]
                    break
        elif isinstance(methods_api_data, dict) and "create" in methods_api_data:
            create_method_data = methods_api_data["create"]

        if not create_method_data:
            logger.debug(f"No create method found for entity {entity_name}")
            return ""

        # Get parameters from create method
        api_params_list = create_method_data.get(
            "parameters", create_method_data.get("params", [])
        )
        if not isinstance(api_params_list, list):
            logger.warning(
                f"Parameters for create method in {entity_name} are not a list. Treating as empty."
            )
            return ""

        # Parse all parameters
        parsed_params = self.parse_api_parameters(api_params_list)

        # Look for the entity parameter (singular form of entity_name if needed)
        entity_param_name = entity_name
        if entity_name.endswith("s") and entity_name[-2:] != "ss":
            entity_param_name = entity_name[:-1]
        # If we find the entity parameter and it has children, use those for init params
        if entity_param_name in parsed_params and parsed_params[entity_param_name]["children"]:
            entity_children = parsed_params[entity_param_name]["children"]

            # Generate typed parameters for __init__ from the entity's children
            required_params, optional_params = [], []
            for name, details in entity_children.items():
                fixed_name = self.fix_name(name)
                type_annotation = self.get_python_type_annotation(details, param_name=name)

                if "= None" in type_annotation:
                    optional_params.append(f"{fixed_name}: {type_annotation}")
                else:
                    required_params.append(f"{fixed_name}: {type_annotation}")

            # Format the parameters with proper indentation
            param_lines = required_params + optional_params
            return ",\n        ".join(param_lines)

        return ""

    def fill_method_template_custom(self, class_name, method_name_raw, method_api_data):
        """Generate method code from template"""
        logger.debug(f"Filling method template for {class_name}.{method_name_raw}")

        template_str = self._load_template("method")
        if not template_str:
            return ""

        method_name = self.fix_name(method_name_raw)

        # Process API parameters
        api_params_list = method_api_data.get("parameters", method_api_data.get("params", []))
        if not isinstance(api_params_list, list):
            logger.warning(
                "Parameters for %s are not a list: %s. Treating as empty.",
                method_name_raw,
                api_params_list,
            )
            api_params_list = []

        parsed_params = self.parse_api_parameters(api_params_list)

        # Special handling for create method
        self_param_inject = ""
        entity_param_name = class_name.lower()

        if method_name_raw == "create" and parsed_params.pop(entity_param_name, None):
            logger.debug(
                f"Found self-referential parameter '{entity_param_name}' in {class_name}.create"
            )
            self_param_inject = f'\n    params["{entity_param_name}"] = self'

        typed_parameters_str = self.generate_typed_parameters_string(parsed_params)

        # Process paths
        paths_list = method_api_data.get("paths", [])
        if not isinstance(paths_list, list):
            logger.warning(
                "Paths for %s are not a list: %s. Treating as empty.",
                method_name_raw,
                paths_list,
            )
            paths_list = []

        compiled_paths_str = str(self.compile_paths(paths_list))

        # Check if ID parameter is required
        has_id_param = any(name == "id" for name, details in parsed_params.items())
        id_snip = "\n    id = self.id  # set for params" if has_id_param else ""

        # Apply template replacements
        replacements = {
            "method_name": method_name,
            "typed_parameters": typed_parameters_str,
            "path_list": compiled_paths_str,
            "id_snip_if_needed": id_snip,
            "self_param_inject": self_param_inject,
        }

        return self.template_manager.replace_placeholders(template_str, replacements)

    def fill_entity_template_custom(self, entity_name, entity_api_data):
        """Generate entity class code from template"""
        logger.debug(f"Filling entity template for {entity_name}")

        template_str = self._load_template("class")
        if not template_str:
            return ""

        class_name = self.name_to_class(entity_name)

        # Extract initialization parameters from create method
        init_params = self.extract_init_params_from_create_method(entity_name, entity_api_data)

        # Track renamed methods for patch_methods decorator
        renamed_methods = {}
        methods_api_data = entity_api_data.get("methods", [])
        all_method_definitions = []

        # Process methods based on data structure
        all_method_definitions = self._process_methods(
            methods_api_data, entity_name, class_name, renamed_methods
        )

        # Apply patch_methods decorator if there are any renamed methods
        class_definition = f"class {class_name}({self.name_to_class(self.api_name)}):"
        if renamed_methods:
            class_definition = f"@patch_methods({renamed_methods})\n{class_definition}"

        # Indent method definitions appropriately
        methods_str = shift_text("\n".join(all_method_definitions), shift=1)

        # Apply template replacements
        replacements = {
            "FeatureName": class_name,
            "ProductName": self.name_to_class(self.api_name),
            "init_params": init_params,
            "class methods": methods_str,
        }

        template_str = self.template_manager.replace_placeholders(template_str, replacements)

        # Replace class definition if we have renamed methods
        if renamed_methods:
            template_str = template_str.replace(
                f"class {class_name}({self.name_to_class(self.api_name)}):", class_definition
            )

        return template_str

    def _process_methods(self, methods_api_data, entity_name, class_name, renamed_methods):
        """Process methods data and generate method definitions"""
        all_method_definitions = []

        # Handle both list and dict formats for methods
        if isinstance(methods_api_data, list):
            # List format: [{method_name: {method_data}}, {method_name2: {method_data2}}]
            for method_dict in methods_api_data:
                if isinstance(method_dict, dict):
                    for raw_method_name, method_data in method_dict.items():
                        # Save original name before fixing
                        original_name = raw_method_name
                        fixed_name = self.fix_name(raw_method_name)

                        # If name was changed, record the mapping
                        if original_name != fixed_name:
                            renamed_methods[original_name] = fixed_name

                        all_method_definitions.append(
                            self.fill_method_template_custom(
                                class_name, raw_method_name, method_data
                            )
                        )
                else:
                    # Handle the case where it's just a list of method names
                    logger.warning(
                        f"Method data for {method_dict} in {entity_name} is not a dictionary"
                    )
        elif isinstance(methods_api_data, dict):
            # Dict format: {method_name: {method_data}, method_name2: {method_data2}}
            for raw_method_name, method_data in methods_api_data.items():
                # Save original name before fixing
                original_name = raw_method_name
                fixed_name = self.fix_name(raw_method_name)

                # If name was changed, record the mapping
                if original_name != fixed_name:
                    renamed_methods[original_name] = fixed_name

                all_method_definitions.append(
                    self.fill_method_template_custom(class_name, raw_method_name, method_data)
                )
        else:
            logger.warning(
                "Methods data for %s is neither a list nor a dictionary: %s",
                entity_name,
                type(methods_api_data),
            )

        return all_method_definitions

    def generate_ff_type_classes(self):
        """Generate the content for the ffTypes class based on encountered types"""
        if not self.ff_types:
            return "pass  # No custom types needed"

        template_f = Path("libs/templates/typed/ff_class.template")
        if not template_f.exists():
            logger.error(f"Unable to find ff_class template: {template_f.absolute()}")
            return "pass  # Template not found"

        with template_f.open("r") as f:
            template_str = f.read()

        class_definitions = []
        for type_name, method_name in sorted(self.ff_types):
            class_def = template_str.replace("~~ff_type~~", type_name)
            class_def = class_def.replace("~~ff_method~~", method_name)
            class_definitions.append(class_def)

        return "\n    ".join(class_definitions)

    def create_custom_lib_file(self):
        """Create the custom library file for the API"""
        logger.info(f"Creating custom library file for API: {self.api_name} v{self.api_version}")

        # Generate entity templates
        all_entity_templates = []
        for entity_name, entity_api_data in self.api_dict.items():
            if not isinstance(entity_api_data, dict):
                logger.warning(f"Skipping entity {entity_name} as its data is not a dictionary.")
                continue
            all_entity_templates.append(
                self.fill_entity_template_custom(entity_name, entity_api_data)
            )

        all_entity_templates_str = "\n\n".join(filter(None, all_entity_templates))

        # Load main template
        loaded_main_template = self._load_template("main")
        if not loaded_main_template:
            return

        # Generate the ff_type_classes content
        ff_type_classes = self.generate_ff_type_classes()

        # Apply template replacements
        replacements = {
            "ProductName": self.name_to_class(self.api_name),
            "feature classes": all_entity_templates_str,
            "ff_type_classes": ff_type_classes,
        }

        loaded_main_template = self.template_manager.replace_placeholders(
            loaded_main_template, replacements
        )

        # Save the generated file
        save_file = Path(f"libs/generated/typed/{self.api_version}/{self.api_name}.py")
        save_file.parent.mkdir(parents=True, exist_ok=True)

        # Write the file and format it
        self._write_and_format_file(save_file, loaded_main_template)

    def _write_and_format_file(self, file_path, content):
        """Write content to file and format with ruff"""
        if file_path.exists():
            logger.warning(f"Overwriting {file_path}")
            file_path.unlink()

        logger.info(f"Saving results to {file_path}")
        file_path.write_text(content)

        logger.info(f"running ruff on {file_path}")
        try:
            subprocess.run(["ruff", "format", str(file_path)], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Ruff linting failed: {e}")


class TypedMaker:
    def __init__(self, api_dict, api_name, api_version):
        self.api_dict = api_dict
        self.api_name = api_name
        self.api_version = api_version

    def make(self):
        """Make all the changes needed to create the typed library version"""
        logger.info(
            f"Starting typed library generation for API: {self.api_name} v{self.api_version}"
        )
        if not self.api_dict:
            logger.error("API dictionary is empty. Cannot generate library.")
            return

        entity_maker = CustomEntityMaker(self.api_dict, self.api_name, self.api_version)
        entity_maker.create_custom_lib_file()
        logger.info(
            f"Successfully generated typed library for API: {self.api_name} v{self.api_version}"
        )
