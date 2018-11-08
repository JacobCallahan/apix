# -*- encoding: utf-8 -*-
"""A collection of miscellaneous helpers that don't quite fit in."""
import yaml
from pathlib import Path


def get_api_list(mock=False):
    """Return a list of saved apis, if they exist"""
    api_dir = Path("APIs/" if not mock else "tests/APIs/")
    # check exists
    if not api_dir.exists():
        return None
    # get all versions in directory, that aren't diffs
    apis = [
        (api.name, api.stat().st_mtime) for api in api_dir.iterdir() if api.is_dir()
    ] or []
    apis = [api for api, _ in sorted(apis, key=lambda x: x[1], reverse=True)]
    return apis


def get_ver_list(api_name, mock=False):
    """Return a list of saved api versions, if they exist"""
    if mock:
        save_path = Path(f"tests/APIs/{api_name}")
    else:
        save_path = Path(f"APIs/{api_name}")
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
    return sorted(versions, reverse=True)


def get_latest(api_name=None, mock=False):
    """Get the latest api version, if it exists"""
    if not api_name:
        return get_api_list(mock=mock)[0]
    else:
        ver_list = get_ver_list(api_name, mock=mock) or [None]
        return ver_list[0]


def get_previous(api_name, version, mock=False):
    """Get the api version before `version`, if it isn't last"""
    api_list = get_ver_list(api_name, mock=mock)
    if version in api_list:
        v_pos = api_list.index(version)
        if v_pos + 2 <= len(api_list):
            return api_list[v_pos + 1]
    return None


def load_api(api_name, version, mock=False):
    """Load the saved yaml to dict, if the file exists"""
    if mock:
        a_path = Path(f"tests/APIs/{api_name}/{version}.yaml")
    else:
        a_path = Path(f"APIs/{api_name}/{version}.yaml")

    if not a_path.exists():
        return None
    return yaml.load(a_path.open("r")) or None
