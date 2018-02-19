# -*- encoding: utf-8 -*-
"""Tests for apix.helpers."""
from pathlib import Path
import pytest
from apix import helpers


def test_positive_get_api_list():
    api_list = helpers.get_api_list(mock=True)
    assert api_list
    assert 'test123' in api_list


def test_positive_get_ver_list():
    ver_list = helpers.get_ver_list(api_name='test123', mock=True)
    assert ver_list
    assert '1.3' in ver_list
    assert '2.1' in ver_list


def test_negative_get_ver_list():
    assert not helpers.get_ver_list(api_name='negative', mock=True)


def test_positive_get_latest():
    assert helpers.get_latest(api_name='test123', mock=True) == '2.1'


def test_negative_get_latest():
    assert not helpers.get_latest(api_name='negative', mock=True)


def test_positive_get_previous():
    assert helpers.get_previous('test123', version='2.1', mock=True) == '1.3'


def test_negative_get_previous():
    assert not helpers.get_previous('test123', version='1.3', mock=True)


def test_positive_load_api():
    loaded = helpers.load_api(api_name='test123', version='2.1', mock=True)
    assert loaded
    assert isinstance(loaded, dict)
    assert 'entity_one' in loaded


def test_negative_load_api():
    assert not helpers.load_api(api_name='test123', version='3.9', mock=True)
