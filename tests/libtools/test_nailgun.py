# -*- encoding: utf-8 -*-
"""Tests for apix.diff."""
from pathlib import Path
import pytest
from apix.helpers import load_api
from apix.libtools import nailgun


def test_positive_name_to_proper_name():
    assert nailgun.EntityMaker.name_to_proper_name("name") == "Name"
    assert nailgun.EntityMaker.name_to_proper_name("entity_name") == "Entity Name"
    assert nailgun.EntityMaker.name_to_proper_name("entity_names") == "Entity Name"


def test_positive_name_to_class():
    assert nailgun.EntityMaker.name_to_class("name") == "Name"
    assert nailgun.EntityMaker.name_to_class("entity_name") == "EntityName"
    assert nailgun.EntityMaker.name_to_class("entity_names") == "EntityName"


def test_positive_normalize_param_name():
    assert nailgun.EntityMaker.normalize_param_name("param") == "param"
    assert nailgun.EntityMaker.normalize_param_name("param_id") == "param"
    assert nailgun.EntityMaker.normalize_param_name("param_ids") == "param"
    assert nailgun.EntityMaker.normalize_param_name("pass[param]") == "param"
    assert nailgun.EntityMaker.normalize_param_name("pass[skip][param]") == "param"


def test_positive_get_base_params():
    api_dict = load_api("test123", "2.1", "./", True)
    base_params = nailgun.EntityMaker.get_base_params(api_dict["entity_one"])
    assert base_params
    seen = []
    for param in base_params:
        assert "~" in param
        assert param not in seen
        seen.append(param)


def test_positive_get_field_type():
    params = {
        "param_id ~ optional ~ nothing": "OneToOneField",
        "param_ids ~ optional ~ nothing": "OneToManyField",
        "Upper ~ optional ~ thing[mail]": "EmailField",
        "param_date ~ optional ~ nothing": "DateField",
        "param[ip] ~ optional ~ nothing": "IPAddressField",
        "subnet[from] ~ optional ~ nothing": "IPAddressField",
        "param[something][mask] ~ optional ~ nothing": "NetMaskField",
        "param[mac] ~ optional ~ nothing": "MACAddressField",
        "param_url ~ optional ~ nothing": "URLField",
        "param ~ optional ~ nothing true, false": "BooleanField",
        "param ~ optional ~ array of nothings": "ListField",
        "param ~ optional ~ datetime": "DateTimeField",
        "param ~ optional ~ hash of nothing": "DictField",
        "param ~ optional ~ thing of numbers": "IntegerField",
        "param ~ optional ~ integer": "IntegerField",
        "param ~ optional ~ String thing": "StringField",
        "param ~ optional ~ nothing": "StringField",
    }
    for param, expected in params.items():
        assert nailgun.EntityMaker.get_field_type(param) == expected


def test_positive_arg_override():
    assert nailgun.EntityMaker.arg_override("Location", "Environment") == "Environment"
    assert (
        nailgun.EntityMaker.arg_override("ActivationKey", "Environment")
        == "LifecycleEnvironment"
    )
    assert nailgun.EntityMaker.arg_override("Something", "Else") == "Else"


def test_positive_get_method_paths():
    api_dict = load_api("test123", "2.1", "./", True)
    emaker = nailgun.EntityMaker(api_dict, "test123", "2.1")
    meth_paths = emaker.get_method_paths("entity_one")
    assert "update" in meth_paths
    assert meth_paths["meth3"][0] == "GET /test123/api/entity_one/:id/meth3"


def test_positive_get_base_path():
    api_dict = load_api("test123", "2.1", "./", True)
    emaker = nailgun.EntityMaker(api_dict, "test123", "2.1")
    assert emaker.get_base_path("entity_two") == "api/entity_two"


def test_positive_entity_to_field():
    api_dict = load_api("test123", "2.1", "./", True)
    emaker = nailgun.EntityMaker(api_dict, "test123", "2.1")
    field = emaker.param_to_field(
        class_name="entity_one",
        param="param1  ~ required ~ string from 2 to 128 characters alphanumeric",
    )
    assert field == (
        "'param1': entity_fields.StringField("
        + "required=True, str_type='alpha', length=(2, 128))"
    )
