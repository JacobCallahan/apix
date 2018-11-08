# -*- encoding: utf-8 -*-
"""
Provides a class with methods that parse the api correctly.

Parser classes must currently implement the following methods:
    pull_links - Returns a list of links to visit from the API's base url.
    yaml_format - Returns yaml-friendly dict of the compiled data.
    scrape_content - Returns a dict of params and paths from a single page.

https://www.google.com/search?q=apix
"""
import attr
from logzero import logger
from lxml import html


@attr.s()
class TestParser:
    """Parser class for testing purposes only."""

    _data = attr.ib(default={}, repr=False)

    def _data_to_yaml(self, index):
        """Translate a url and text into 'paths' and 'parameters'"""
        url = index
        split_url = url.split(".")
        name = split_url[-1]
        first = self._data[index][0]
        rest = " ~ ".join(self._data[index][1:])
        return url, {name: {"paths": first, "parameters": rest}}

    def yaml_format(self, data):
        """compile all data into a yaml-compatible dict"""
        self._data, yaml_data = data, {}
        for index in self._data:
            ent, res = self._data_to_yaml(index)
            if ent and not yaml_data.get(ent, None):
                yaml_data[ent] = {"content": [res]}
            elif ent:
                yaml_data[ent]["content"].append(res)
        return yaml_data

    @staticmethod
    def pull_links(result, base_path):
        """return all desired links from the target page"""
        g_links = html.fromstring(result.content).iterlinks()
        links, last = [], None
        for link in g_links:
            url = link[2].replace("../", "")
            if (
                "JacobCallahan" in url
                and "sparkline" not in url
                and link[0].text
                and url != last
            ):
                links.append((link[0].text, url))
                last = url
        return links

    @staticmethod
    def scrape_content(content):
        """take the title text from a page, if it exists"""
        tree = html.fromstring(content)
        title = tree.xpath("//head/title")
        if title:
            title = title[0].text
        else:
            title = "This page had no title for some reason"
        return [x.strip() for x in title.split() if x]
