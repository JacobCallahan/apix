# -*- encoding: utf-8 -*-
"""Determine the changes between two API versions."""
import attr
import yaml
from pathlib import Path
from logzero import logger
from apix.helpers import get_latest, get_previous, load_api


@attr.s()
class VersionDiff():
    api_name = attr.ib(default=None)
    ver1 = attr.ib(default=None)
    ver2 = attr.ib(default=None)
    _vdiff = attr.ib(default={})

    def __attrs_post_init__(self):
        """Load the API versions, if not provided"""
        if not self.api_name:
            self.api_name = get_latest()
        if not self.ver1:
            # get the latest saved version
            self.ver1 = get_latest(self.api_name)
        if not self.ver2:
            # get the version before ver1
            self.ver2 = get_previous(self.api_name, self.ver1)

    def _dict_diff(self, dict1, dict2):
        """Recursively search a dictionary for differences"""
        added = {}
        if dict1 == dict2:
            return added
        for key, values in dict1.items():
            if key in dict2:
                if not values == dict2[key]:
                    if isinstance(values, dict):
                        res = self._dict_diff(values, dict2[key])
                        if res:
                            added[key] = res
                    elif isinstance(values, list):
                        res = self._list_diff(values, dict2[key])
                        if res:
                            added[key] = res
                    else:
                        logger.debug('Adding {} => {}'.format(key, values))
                        added[key] = values
            else:
                logger.debug('Adding {} => {}'.format(key, values))
                added[key] = values
        return added


    def _list_diff(self, list1, list2):
        """Recursively search a list for differences"""
        added = []
        if list1 == list2:
            return added
        for item in list1:
            if isinstance(item, dict):
                found = False
                for key in item:
                    for i, needle in enumerate(list2):
                        if key in needle:
                            found = True
                            res = self._dict_diff(item, list2[i])
                            if res:
                                added.append(res)
                if not found:
                    logger.debug('Adding {}'.format(item))
                    added.append(item)
            elif isinstance(item, list):
                res = self._list_diff(item, list2[list2.index(item)])
                if res:
                    added.append(res)
            else:
                if item not in list2:
                    logger.debug('Adding {}'.format(item))
                    added.append(item)
        return added

    def diff(self):
        """Determine the diff between ver1 and ver2"""
        if not self.ver1:
            logger.warning("No ver1 API found.")
            return None
        if not self.ver2:
            logger.warning("No ver2 API found.")
            return None
        logger.info('Performing diff between {} and {}'.format(self.ver1, self.ver2))

        ver1_content = load_api(self.api_name, self.ver1)
        logger.debug('Loaded {}'.format(self.ver1))
        ver2_content = load_api(self.api_name, self.ver2)
        logger.debug('Loaded {}'.format(self.ver1))

        added = self._dict_diff(ver1_content, ver2_content)
        logger.debug('Determined added content.')
        removed = self._dict_diff(ver2_content, ver1_content)
        logger.debug('Determined removed content.')
        self._vdiff = {
            'Added in {} since {}'.format(self.ver1, self.ver2): added,
            'Removed since {}'.format(self.ver2): removed
        }

    def save_diff(self):
        """Save the currently stored diff"""
        if not self._vdiff:
            logger.warning('No data to be saved. Exiting.')
            return

        fpath = Path('APIs/{}/{}-to-{}-diff.yaml'.format(
            self.api_name, self.ver2, self.ver1
        ))
        if fpath.exists():
            fpath.unlink()
        # create the directory, if it doesn't exist
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()
        logger.info('Saving results to {}'.format(fpath))
        with fpath.open('w+') as outfile:
            yaml.dump(self._vdiff, outfile, default_flow_style=False)
