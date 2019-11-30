# -*- encoding: utf-8 -*-
"""A collection of miscellaneous helpers that don't quite fit in."""
import re
import yaml
from copy import deepcopy
from distutils.version import StrictVersion
from logzero import logger
from pathlib import Path


class LooseVersion(StrictVersion):
    """This class adds the characters 's' and '-' to those allowed by StrictVersion"""

    version_re = re.compile(
        r"^(\d+) \. (\d+) (\. (\d+))? ([abs-](\d+))?$", re.VERBOSE | re.ASCII
    )


def get_api_list(data_dir=None, mock=False):
    """Return a list of saved apis, if they exist"""
    api_dir = Path(f"{data_dir}APIs/" if not mock else f"{data_dir}tests/APIs/")
    # check exists
    if not api_dir.exists():
        return None
    # get all apis in directory
    apis = [api.name for api in api_dir.iterdir() if api.is_dir()] or []
    apis.sort(reverse=True)
    return apis


def get_ver_list(api_name, data_dir=None, mock=False):
    """Return a list of saved api versions, if they exist"""
    if mock:
        save_path = Path(f"{data_dir}tests/APIs/{api_name}")
    else:
        save_path = Path(f"{data_dir}APIs/{api_name}")
    # check exists
    if not save_path.exists():
        return None
    # get all versions in directory, that aren't diffs
    versions = [
        v_file.name.replace(".yaml", "")
        for v_file in save_path.iterdir()
        if "-diff." not in v_file.name
        and "-comp." not in v_file.name
        and ".yaml" in v_file.name
    ] or []
    try:
        versions.sort(key=LooseVersion, reverse=True)
    except ValueError as err:
        logger.error(f"Encountered an invalid version number. Stopping\n{err}")
        return None
    return versions


def get_latest(api_name=None, data_dir=None, mock=False):
    """Get the latest api version, if it exists"""
    if not api_name:
        return get_api_list(data_dir, mock=mock)[0]
    else:
        ver_list = get_ver_list(api_name, data_dir, mock=mock) or [None]
        return ver_list[0]


def get_previous(api_name, version, data_dir=None, mock=False):
    """Get the api version before `version`, if it isn't last"""
    api_list = get_ver_list(api_name, data_dir, mock=mock)
    if api_list and version in api_list:
        v_pos = api_list.index(version)
        if v_pos + 2 <= len(api_list):
            return api_list[v_pos + 1]
    return None


def shift_text(text, shift=1):
    """Shifts blocks or a single line of text by 4 * shift spaces"""
    new_text = ""
    if "\n" in text:
        for line in text.split("\n"):
            new_text += "    " * shift + line + "\n"
    else:
        new_text = "    " * shift + text
    return new_text


def load_api(api_name, version, data_dir=None, mock=False):
    """Load the saved yaml to dict, if the file exists"""
    if mock:
        a_path = Path(f"{data_dir}tests/APIs/{api_name}/{version}.yaml")
    else:
        a_path = Path(f"{data_dir}APIs/{api_name}/{version}.yaml")
    if not a_path.exists():
        return None
    return yaml.load(a_path.open("r")) or None


def merge_dicts(dict1, dict2):
    """Merge two nested dicitonaries together"""
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return dict1
    merged = {}
    dupe_keys = dict1.keys() & dict2.keys()
    for key in dupe_keys:
        merged[key] = merge_dicts(dict1[key], dict2[key])
    for key in dict1.keys() - dupe_keys:
        merged[key] = deepcopy(dict1[key])
    for key in dict2.keys() - dupe_keys:
        merged[key] = deepcopy(dict2[key])
    return merged
