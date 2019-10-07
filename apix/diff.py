# -*- encoding: utf-8 -*-
"""Determine the changes between two API versions."""
import attr
import yaml
from pathlib import Path
from logzero import logger
from apix.helpers import get_latest, get_previous, load_api


@attr.s()
class VersionDiff:
    api_name = attr.ib(default=None)
    ver1 = attr.ib(default=None)
    ver2 = attr.ib(default=None)
    data_dir = attr.ib(default=None)
    compact = attr.ib(default=False)
    mock = attr.ib(default=False, repr=False)
    _vdiff = attr.ib(default={})

    def __attrs_post_init__(self):
        """Load the API versions, if not provided"""
        if not self.api_name:
            self.api_name = get_latest(data_dir=self.data_dir, mock=self.mock)
        if not self.ver1:
            # get the latest saved version
            self.ver1 = get_latest(
                api_name=self.api_name, data_dir=self.data_dir, mock=self.mock
            )
        if not self.ver2:
            # get the version before ver1
            self.ver2 = get_previous(self.api_name, self.ver1, self.data_dir, self.mock)

    @staticmethod
    def _truncate(diff_dict):
        """Strip all extra information from a diff"""
        compact_diff = {}
        for parent, children in diff_dict.items():
            compact_diff[parent] = []
            for meth in children["methods"]:
                compact_diff[parent].append(list(meth.keys())[0])
        return compact_diff

    def _dict_diff(self, dict1, dict2):
        """Recursively search a dictionary for differences"""
        added, changed = {}, {}
        if dict1 == dict2:
            return added, changed
        for key, values in dict1.items():
            if key in dict2:
                if not values == dict2[key]:
                    if isinstance(values, dict):
                        res, chng = self._dict_diff(values, dict2[key])
                        if res:
                            added[key] = res
                        if chng:
                            changed[key] = chng
                    elif isinstance(values, list):
                        res, chng = self._list_diff(values, dict2[key])
                        if res:
                            added[key] = res
                        if chng:
                            changed[key] = chng
                    else:
                        logger.debug(f"Adding {key} => {values}")
                        added[key] = values
            else:
                logger.debug(f"Adding {key} => {values}")
                added[key] = values
        return added, changed

    def _list_diff(self, list1, list2):
        """Recursively search a list for differences"""
        added, changed = [], []
        if list1 == list2:
            return added, changed
        for item in list1:
            if isinstance(item, dict):
                found = False
                for key in item:
                    for i, needle in enumerate(list2):
                        if key in needle:
                            found = True
                            res, chng = self._dict_diff(item, list2[i])
                            if res:
                                added.append(res)
                            if chng:
                                changed.append(chng)
                if not found:
                    logger.debug(f"Adding {item}")
                    added.append(item)
            elif isinstance(item, list):
                res, chng = self._list_diff(item, list2[list2.index(item)])
                if res:
                    added.append(res)
                if chng:
                    changed.append(chng)
            elif " ~ " in item:
                name = item.split("~")[0].strip()
                found = False
                for needle in list2:
                    # look for matching names
                    if name == needle.split("~")[0].strip():
                        found = True
                        if item != needle:
                            logger.debug(f"{item} changed to {needle}")
                            changed.append(item)
                if not found:
                    logger.debug(f"Adding {item}")
                    added.append(item)
            else:
                if item not in list2:
                    logger.debug(f"Adding {item}")
                    added.append(item)
        return added, changed

    def diff(self):
        """Determine the diff between ver1 and ver2"""
        if not self.ver1:
            logger.warning("No ver1 API found.")
            return None
        if not self.ver2:
            logger.warning("No ver2 API found.")
            return None
        logger.info(f"Performing diff between {self.ver1} and {self.ver2}")

        ver1_content = load_api(self.api_name, self.ver1, self.data_dir, self.mock)
        logger.debug(f"Loaded {self.ver1}.")
        ver2_content = load_api(self.api_name, self.ver2, self.data_dir, self.mock)
        logger.debug(f"Loaded {self.ver2}.")

        added, changed = self._dict_diff(ver1_content, ver2_content)
        logger.debug("Determined added/changed content.")
        removed, _ = self._dict_diff(ver2_content, ver1_content)
        logger.debug("Determined removed content.")
        if self.compact:
            added = VersionDiff._truncate(added)
            changed = VersionDiff._truncate(changed)
            removed = VersionDiff._truncate(removed)
        self._vdiff = {
            f"Added in {self.ver1} since {self.ver2}": added,
            f"Changed in {self.ver1} since {self.ver2}": changed,
            f"Removed since {self.ver2}": removed,
        }

    def save_diff(self, return_path=False):
        """Save the currently stored diff"""
        if not self._vdiff:
            logger.warning("No data to be saved. Exiting.")
            return

        if self.mock:
            fpath = Path(
                f"{self.data_dir}tests/APIs/{self.api_name}/{self.ver2}-to-{self.ver1}-diff.yaml"
            )
        else:
            ftype = "comp-diff" if self.compact else "diff"
            fpath = Path(
                f"{self.data_dir}APIs/{self.api_name}/{self.ver2}-to-{self.ver1}-{ftype}.yaml"
            )
        if fpath.exists():
            fpath.unlink()
        # create the directory, if it doesn't exist
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()
        logger.info(f"Saving results to {fpath}")
        with fpath.open("w+") as outfile:
            yaml.dump(self._vdiff, outfile, default_flow_style=False)
        if return_path:
            return fpath
