# -*- encoding: utf-8 -*-
"""A collection of miscellaneous helpers that don't quite fit in."""
import yaml
from copy import deepcopy
from pathlib import Path


def get_api_list(data_dir=None, mock=False):
    """Return a list of saved apis, if they exist"""
    api_dir = Path(f"{data_dir}APIs/" if not mock else f"{data_dir}tests/APIs/")
    # check exists
    print(f"API Dir: {api_dir}")
    if not api_dir.exists():
        return None
    # get all versions in directory, that aren't diffs
    apis = [
        (api.name, api.stat().st_mtime) for api in api_dir.iterdir() if api.is_dir()
    ] or []
    apis = [api for api, _ in sorted(apis, key=lambda x: x[1], reverse=True)]
    print(f"APIs: {apis}")
    return apis


def get_ver_list(api_name, data_dir=None, mock=False):
    """Return a list of saved api versions, if they exist"""
    if mock:
        save_path = Path(f"{data_dir}tests/APIs/{api_name}")
    else:
        save_path = Path(f"{data_dir}APIs/{api_name}")
    # check exists
    print(f"save path: {save_path}")
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
    print(f"versions {versions}")
    return sorted(versions, reverse=True)


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
    print(f"prev list: {api_list}")
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
    print(f"load path {a_path}")
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
