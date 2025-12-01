"""Tests for apix.parsers.openapi"""
import json

import pytest

from apix.parsers.openapi import OpenAPI


class MockResponse:
    """Mock HTTP response object"""

    def __init__(self, content):
        if isinstance(content, str):
            self.content = content.encode("utf-8")
        else:
            self.content = content


@pytest.fixture
def openapi_parser():
    """Create a fresh OpenAPI parser instance"""
    return OpenAPI()


@pytest.fixture
def sample_openapi3_spec():
    """Sample OpenAPI 3.0 specification"""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Pet Store API", "version": "1.0.0"},
        "paths": {
            "/pets": {
                "get": {
                    "tags": ["pets"],
                    "operationId": "listPets",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        },
                    ],
                },
                "post": {
                    "tags": ["pets"],
                    "operationId": "createPet",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "tag": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                },
            },
            "/pets/{petId}": {
                "get": {
                    "tags": ["pets"],
                    "operationId": "getPet",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                },
                "delete": {
                    "tags": ["pets"],
                    "operationId": "deletePet",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                },
            },
        },
    }


@pytest.fixture
def sample_swagger2_spec():
    """Sample Swagger 2.0 specification"""
    return {
        "swagger": "2.0",
        "info": {"title": "User API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "tags": ["users"],
                    "operationId": "listUsers",
                    "parameters": [
                        {"name": "page", "in": "query", "type": "integer", "required": False}
                    ],
                },
                "post": {
                    "tags": ["users"],
                    "operationId": "createUser",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "schema": {
                                "type": "object",
                                "required": ["username"],
                                "properties": {
                                    "username": {"type": "string"},
                                    "email": {"type": "string"},
                                },
                            },
                        }
                    ],
                },
            }
        },
    }


def test_openapi_parser_initialization(openapi_parser):
    """Test that OpenAPI parser initializes correctly"""
    assert openapi_parser._data == {}


def test_scrape_content_openapi3_json(openapi_parser, sample_openapi3_spec):
    """Test parsing OpenAPI 3.0 JSON spec"""
    response = MockResponse(json.dumps(sample_openapi3_spec))
    result = openapi_parser.scrape_content(response)

    assert "pets" in result
    assert "methods" in result["pets"]


def test_scrape_content_openapi3_yaml(openapi_parser):
    """Test parsing OpenAPI 3.0 YAML spec"""
    yaml_spec = """
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0"
paths:
  /items:
    get:
      tags:
        - items
      operationId: listItems
      parameters:
        - name: search
          in: query
          required: false
          schema:
            type: string
"""
    response = MockResponse(yaml_spec)
    result = openapi_parser.scrape_content(response)

    assert "items" in result


def test_scrape_content_swagger2(openapi_parser, sample_swagger2_spec):
    """Test parsing Swagger 2.0 spec"""
    response = MockResponse(json.dumps(sample_swagger2_spec))
    result = openapi_parser.scrape_content(response)

    assert "users" in result


def test_yaml_format_output_structure(openapi_parser, sample_openapi3_spec):
    """Test that yaml_format returns the expected structure"""
    response = MockResponse(json.dumps(sample_openapi3_spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    assert "pets" in yaml_data
    assert "methods" in yaml_data["pets"]

    # Check method structure
    methods = yaml_data["pets"]["methods"]
    assert len(methods) > 0

    # Check each method has paths and parameters
    for method in methods:
        for method_data in method.values():
            assert "paths" in method_data
            assert "parameters" in method_data


def test_parameter_status_required(openapi_parser, sample_openapi3_spec):
    """Test that required parameters are marked as required"""
    response = MockResponse(json.dumps(sample_openapi3_spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    # Find getPet method which has a required petId parameter
    for method in yaml_data["pets"]["methods"]:
        if "getPet" in method:
            params = method["getPet"]["parameters"]
            pet_id_param = next((p for p in params if "petId" in p), None)
            assert pet_id_param is not None
            assert "required" in pet_id_param


def test_parameter_status_optional(openapi_parser, sample_openapi3_spec):
    """Test that optional parameters are marked as optional"""
    response = MockResponse(json.dumps(sample_openapi3_spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    # Find listPets method which has optional limit parameter
    for method in yaml_data["pets"]["methods"]:
        if "listPets" in method:
            params = method["listPets"]["parameters"]
            limit_param = next((p for p in params if "limit" in p), None)
            assert limit_param is not None
            assert "optional" in limit_param


def test_http_method_in_paths(openapi_parser, sample_openapi3_spec):
    """Test that HTTP methods are included in paths"""
    response = MockResponse(json.dumps(sample_openapi3_spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    # Check that paths include HTTP method
    for method in yaml_data["pets"]["methods"]:
        for method_data in method.values():
            for path in method_data["paths"]:
                # Path should start with HTTP method
                assert any(
                    path.startswith(m) for m in ["GET", "POST", "PUT", "PATCH", "DELETE"]
                )


def test_request_body_parameters(openapi_parser, sample_openapi3_spec):
    """Test that request body properties are extracted as parameters"""
    response = MockResponse(json.dumps(sample_openapi3_spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    # Find createPet method
    for method in yaml_data["pets"]["methods"]:
        if "createPet" in method:
            params = method["createPet"]["parameters"]
            # Check that body properties are included
            name_param = next((p for p in params if "name" in p and "required" in p), None)
            assert name_param is not None
            tag_param = next((p for p in params if "tag" in p and "optional" in p), None)
            assert tag_param is not None


def test_swagger2_body_parameters(openapi_parser, sample_swagger2_spec):
    """Test that Swagger 2.0 body parameters are extracted"""
    response = MockResponse(json.dumps(sample_swagger2_spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    # Find createUser method
    for method in yaml_data["users"]["methods"]:
        if "createUser" in method:
            params = method["createUser"]["parameters"]
            # Check that body properties are included
            username_param = next(
                (p for p in params if "username" in p and "required" in p), None
            )
            assert username_param is not None


def test_empty_spec(openapi_parser):
    """Test handling of empty spec"""
    response = MockResponse("{}")
    result = openapi_parser.scrape_content(response)
    assert result == {}


def test_invalid_json(openapi_parser):
    """Test handling of invalid JSON (tries YAML fallback)"""
    response = MockResponse("not valid json or yaml: [[[")
    result = openapi_parser.scrape_content(response)
    assert result == {}


def test_deprecated_parameter(openapi_parser):
    """Test that deprecated parameters are marked correctly"""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/test": {
                "get": {
                    "parameters": [
                        {
                            "name": "old_param",
                            "in": "query",
                            "deprecated": True,
                            "schema": {"type": "string"},
                        }
                    ]
                }
            }
        },
    }
    response = MockResponse(json.dumps(spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    # Check that the deprecated parameter is marked as deprecated
    for entity in yaml_data.values():
        for method in entity["methods"]:
            for method_data in method.values():
                for param in method_data["parameters"]:
                    if "old_param" in param:
                        assert "deprecated" in param


def test_array_parameter_type(openapi_parser):
    """Test that array parameters show item type"""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/test": {
                "get": {
                    "parameters": [
                        {
                            "name": "ids",
                            "in": "query",
                            "schema": {"type": "array", "items": {"type": "integer"}},
                        }
                    ]
                }
            }
        },
    }
    response = MockResponse(json.dumps(spec))
    openapi_parser.scrape_content(response)
    yaml_data = openapi_parser.yaml_format()

    for entity in yaml_data.values():
        for method in entity["methods"]:
            for method_data in method.values():
                for param in method_data["parameters"]:
                    if "ids" in param:
                        assert "array of integer" in param


def test_entity_extraction_from_tags(openapi_parser):
    """Test that entity is extracted from tags"""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/api/v1/something": {
                "get": {
                    "tags": ["Custom Entity"],
                    "operationId": "getSomething",
                }
            }
        },
    }
    response = MockResponse(json.dumps(spec))
    result = openapi_parser.scrape_content(response)

    assert "custom_entity" in result


def test_entity_extraction_from_path(openapi_parser):
    """Test that entity is extracted from path when no tags"""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/api/v1/products/{id}": {
                "get": {
                    "operationId": "getProduct",
                }
            }
        },
    }
    response = MockResponse(json.dumps(spec))
    result = openapi_parser.scrape_content(response)

    assert "products" in result


def test_get_param_status(openapi_parser):
    """Test _get_param_status method"""
    assert openapi_parser._get_param_status({"deprecated": True}) == "deprecated"
    assert openapi_parser._get_param_status({"required": True}) == "required"
    assert openapi_parser._get_param_status({}) == "optional"
    # Deprecated takes precedence
    assert openapi_parser._get_param_status({"deprecated": True, "required": True}) == "deprecated"
