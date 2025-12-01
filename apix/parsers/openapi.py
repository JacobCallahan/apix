"""
Provides a class with methods that parse OpenAPI specifications.

Parser classes must currently implement the following methods:
    yaml_format - Returns yaml-friendly dict of the compiled data.
    scrape_content - Returns a dict of params and paths from a single page.

OpenAPI parsers work differently from page-based parsers:
    - They don't need pull_links since OpenAPI specs are self-contained
    - They parse the entire spec in one scrape_content call
"""
import json

from loguru import logger
import yaml


class OpenAPI:
    """Parser class for OpenAPI (Swagger) specifications"""

    def __init__(self):
        self._data = {}

    @staticmethod
    def _get_param_type(param):
        """Extract the parameter type from OpenAPI schema"""
        if "schema" in param:
            schema = param["schema"]
            if "$ref" in schema:
                # Extract type from reference like #/components/schemas/Pet
                return schema["$ref"].split("/")[-1]
            if "type" in schema:
                param_type = schema["type"]
                if param_type == "array" and "items" in schema:
                    items = schema["items"]
                    if "$ref" in items:
                        item_type = items["$ref"].split("/")[-1]
                    else:
                        item_type = items.get("type", "any")
                    return f"array of {item_type}"
                return param_type
        # OpenAPI 2.0 style
        if "type" in param:
            param_type = param["type"]
            if param_type == "array" and "items" in param:
                item_type = param["items"].get("type", "any")
                return f"array of {item_type}"
            return param_type
        return "any"

    @staticmethod
    def _get_request_body_params(request_body, prefix=""):
        """Extract parameters from request body schema"""
        params = []
        if not request_body:
            return params

        content = request_body.get("content", {})
        # Check for JSON content first, then any other content type
        schema = None
        for content_type in ["application/json", "application/x-www-form-urlencoded"]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                break

        if not schema and content:
            # Take the first available content type
            first_content = next(iter(content.values()), {})
            schema = first_content.get("schema", {})

        if not schema:
            return params

        required_fields = set(schema.get("required", []))
        properties = schema.get("properties", {})

        for prop_name, prop_schema in properties.items():
            full_name = f"{prefix}[{prop_name}]" if prefix else prop_name
            status = "required" if prop_name in required_fields else "optional"
            prop_type = prop_schema.get("type", "any")

            if prop_type == "array" and "items" in prop_schema:
                items = prop_schema["items"]
                if "$ref" in items:
                    item_type = items["$ref"].split("/")[-1]
                else:
                    item_type = items.get("type", "any")
                prop_type = f"array of {item_type}"
            elif "$ref" in prop_schema:
                prop_type = prop_schema["$ref"].split("/")[-1]

            params.append(f"{full_name} ~ {status} ~ {prop_type}")

            # Handle nested objects
            if prop_schema.get("type") == "object" and "properties" in prop_schema:
                nested_required = set(prop_schema.get("required", []))
                for nested_name, nested_schema in prop_schema["properties"].items():
                    nested_full_name = f"{full_name}[{nested_name}]"
                    nested_status = "required" if nested_name in nested_required else "optional"
                    nested_type = nested_schema.get("type", "any")
                    params.append(f"{nested_full_name} ~ {nested_status} ~ {nested_type}")

        return params

    @staticmethod
    def _extract_entity_from_path(path, tags):
        """Extract entity name from path or tags"""
        # Use tags if available
        if tags:
            return tags[0].lower().replace(" ", "_")
        # Otherwise extract from path
        # /api/v1/users/{id} -> users
        # /pets/{petId}/orders -> pets
        parts = path.strip("/").split("/")
        for part in parts:
            if not part.startswith("{") and part not in ("api", "v1", "v2", "v3"):
                return part.lower()
        return "unknown"

    @staticmethod
    def _extract_method_name(operation_id, http_method, path):
        """Extract a meaningful method name"""
        if operation_id:
            return operation_id

        # Generate from path and method
        parts = path.strip("/").split("/")
        # Filter out path parameters and api versions
        meaningful_parts = [
            p for p in parts if not p.startswith("{") and p not in ("api", "v1", "v2", "v3")
        ]

        if meaningful_parts:
            base = meaningful_parts[-1]
            method_map = {
                "get": "list" if not any(p.startswith("{") for p in parts) else "read",
                "post": "create",
                "put": "update",
                "patch": "update",
                "delete": "destroy",
            }
            return f"{method_map.get(http_method.lower(), http_method.lower())}_{base}"

        return f"{http_method.lower()}_operation"

    def _get_param_status(self, param):
        """Determine parameter status (required/optional/deprecated)"""
        if param.get("deprecated", False):
            return "deprecated"
        if param.get("required", False):
            return "required"
        return "optional"

    def _compile_operation_params(self, operation):
        """Compile all parameters from an operation"""
        params = []

        # Handle standard parameters
        for param in operation.get("parameters", []):
            name = param.get("name", "unknown")
            status = self._get_param_status(param)
            param_type = self._get_param_type(param)
            params.append(f"{name} ~ {status} ~ {param_type}")

        # Handle request body (OpenAPI 3.x)
        if "requestBody" in operation:
            body_params = self._get_request_body_params(operation["requestBody"])
            params.extend(body_params)

        # Handle body parameter (Swagger 2.0)
        params.extend(self._compile_swagger2_body_params(operation))

        return params

    def _compile_swagger2_body_params(self, operation):
        """Extract body parameters for Swagger 2.0 style specs"""
        params = []
        for param in operation.get("parameters", []):
            if param.get("in") != "body" or "schema" not in param:
                continue
            schema = param["schema"]
            if "properties" not in schema:
                continue
            required_fields = set(schema.get("required", []))
            for prop_name, prop_schema in schema["properties"].items():
                status = "required" if prop_name in required_fields else "optional"
                prop_type = prop_schema.get("type", "any")
                params.append(f"{prop_name} ~ {status} ~ {prop_type}")
        return params

    def _add_or_update_method(self, entity, method_name, formatted_path, params):
        """Add a new method or update an existing one with additional paths/params.

        Args:
            entity: The entity name (e.g., 'pets', 'users')
            method_name: The method/operation name (e.g., 'createPet', 'listUsers')
            formatted_path: HTTP method and path (e.g., 'GET /pets')
            params: List of parameter strings in format 'name ~ status ~ type'
        """
        for existing_method in self._data[entity]["methods"]:
            if method_name in existing_method:
                existing_method[method_name]["paths"].append(formatted_path)
                # Use set for O(1) lookup of existing params
                existing_params = set(existing_method[method_name].get("params", []))
                new_params = [p for p in params if p not in existing_params]
                existing_method[method_name]["params"].extend(new_params)
                return

        self._data[entity]["methods"].append(
            {method_name: {"paths": [formatted_path], "params": params}}
        )

    def _parse_openapi_spec(self, spec):
        """Parse an OpenAPI specification dictionary"""
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            for http_method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if http_method not in path_item:
                    continue

                operation = path_item[http_method]
                tags = operation.get("tags", [])
                operation_id = operation.get("operationId")

                entity = self._extract_entity_from_path(path, tags)
                method_name = self._extract_method_name(operation_id, http_method, path)

                if entity not in self._data:
                    self._data[entity] = {"methods": []}

                params = self._compile_operation_params(operation)
                formatted_path = f"{http_method.upper()} {path}"
                self._add_or_update_method(entity, method_name, formatted_path, params)

    def scrape_content(self, result):
        """Parse the OpenAPI spec from an HTTP response or raw content.

        Args:
            result: Can be one of:
                - A requests.Response object with a .content attribute
                - Raw bytes containing the OpenAPI spec
                - A string containing the OpenAPI spec (JSON or YAML)
                - Any object with a .content attribute containing bytes

        Returns:
            A dictionary of parsed entities and their methods, or empty dict on error.
        """
        content = result.content if hasattr(result, "content") else result

        # Try to decode if bytes
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        # Try JSON first, then YAML
        try:
            spec = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            try:
                spec = yaml.safe_load(content)
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse OpenAPI spec: {e}")
                return {}

        if not spec:
            logger.warning("Empty OpenAPI spec received")
            return {}

        version = spec.get("openapi", spec.get("swagger", "unknown"))
        logger.debug(f"Parsing OpenAPI spec version: {version}")
        self._parse_openapi_spec(spec)
        return self._data

    def yaml_format(self, ignore=None):
        """Return the compiled data in a yaml-friendly format"""
        # Convert 'params' to 'parameters' for consistency with other parsers
        formatted = {}
        for entity, data in self._data.items():
            formatted[entity] = {"methods": []}
            for method in data["methods"]:
                for method_name, method_data in method.items():
                    formatted[entity]["methods"].append(
                        {
                            method_name: {
                                "paths": method_data.get("paths", []),
                                "parameters": method_data.get("params", []),
                            }
                        }
                    )
        return formatted
