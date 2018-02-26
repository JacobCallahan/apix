# -*- encoding: utf-8 -*-
"""
Provides a class with methods that parse the api correctly.

Parser classes must currently implement the following methods:
    pull_links - Returns a list of links to visit from the API's base url.
    yaml_format - Returns yaml-friendly dict of the compiled data.
    scrape_content - Returns a dict of params and paths from a single page.
"""
import attr
from logzero import logger
from lxml import html


@attr.s()
class APIPie():
    """Parser class for Ruby's APIPie apidoc generator"""
    _data = attr.ib(default={}, repr=False)

    def _data_to_yaml(self, index):
        """translate a url and content into paths and parameters"""
        # apidoc/v2/<entity>/<action>.html
        url = index
        split_url = url.split('/')
        action = split_url[-1].replace('.html', '')
        action = 'list' if action == 'index' else action
        try:
            entity = split_url[-2]
        except Exception as err:
            logger.error(err)
            return False, False

        paths = self._data[index]['paths']
        if '/' not in paths[0]:
            return False, False
        params = self._data[index]['params']
        return entity, {action: {'paths': paths, 'parameters': params}}

    def yaml_format(self, data):
        """compile all data into a yaml-compatible dict"""
        self._data, yaml_data = data, {}
        for index in self._data:
            ent, res = self._data_to_yaml(index)
            if ent and not yaml_data.get(ent, None):
                yaml_data[ent] = {'methods': [res]}
            elif ent:
                yaml_data[ent]['methods'].append(res)
        return yaml_data

    @staticmethod
    def pull_links(result, base_path):
        """return all desired links from the target page"""
        g_links = html.fromstring(result.content).iterlinks()
        links, last = [], None
        for link in g_links:
            url = link[2].replace('../', '')
            if ('/' in url[len(base_path):] and link[0].text
                and url != last):
                links.append((link[0].text, url))
                last = url
        return links

    @staticmethod
    def scrape_content(content):
        """pull the paths and parameters from the h1 and tables on the page"""
        tree = html.fromstring(content)
        paths = tree.xpath("//h1")
        path_list = []
        for path in paths:
            path_list.append(path.text.replace("\n      ",""))
        params = tree.xpath("//table/tbody/tr")
        param_list = []
        for param in params:
            temp_list = [
                x for x
                in param.text_content().replace("  ","").split('\n')
                if x
            ]
            param_list.append(temp_list[:2])
            # If there is a validation, include it in the results
            if 'Validations:' in temp_list:
                param_list[-1].append(temp_list[temp_list.index('Validations:') + 1])
            param_list[-1] = " ~ ".join(param_list[-1])
        return {'paths': path_list, 'params': param_list}
