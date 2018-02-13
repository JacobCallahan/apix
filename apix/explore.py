# -*- encoding: utf-8 -*-
"""Explore and API and save the results."""
import aiofiles
import aiohttp
import asyncio
import async_timeout
import attr
import requests
import time
import yaml
from lxml import html
from logzero import logger
from pathlib import Path


# async def iter_list(inlist):
#     for item in inlist:
#         yield item

@attr.s()
class AsyncExplorer():
    name = attr.ib(default=None)
    version = attr.ib(default=None)
    host_url = attr.ib(default=None)
    base_path = attr.ib(default=None)
    _queue = attr.ib(default=[], repr=False)
    _data = attr.ib(default={}, repr=False)

    def __attrs_post_init__(self):
        if not self.version:
            self.version = time.strftime('%Y-%m-%d', time.localtime())

    async def _async_get(self, session, link):
        async with session.get(self.host_url + link[1], verify_ssl=False) as response:
            content = await response.read()
            logger.debug(link[1])
            return (link, content)

    async def _async_loop(self, links):
        tasks = []
        async with aiohttp.ClientSession() as session:
            for link in links:
                task = asyncio.ensure_future(
                    self._async_get(session, link))
                tasks.append(task)
            results = await asyncio.gather(*tasks)
            for result in results:
                self._queue.append(result)

    def _visit_links(self, links, retries=3):
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._async_loop(links))
        except aiohttp.client_exceptions.ServerDisconnectedError as err:
            logger.warning('Lost connection to host.{}'.join(
                'Retrying in 10 seconds' if retries else ''
            ))
            if retries:
                time.sleep(10)
                self._visit_links(links, retries - 1)

    def _link_params(self):
        while self._queue:
            link, content = self._queue.pop(0)
            logger.debug('Scraping {}'.format(link[1]))
            self._data[link[1]] = self.scrape_content(content)

    def _data_to_yaml(self, index):
        result = {}
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

    def save_data(self):
        yaml_data = {}
        for index in self._data:
            ent, res = self._data_to_yaml(index)
            if ent and not yaml_data.get(ent, None):
                yaml_data[ent] = {'methods': [res]}
            elif ent:
                yaml_data[ent]['methods'].append(res)
        if not yaml_data:
            logger.warning('No data to be saved. Exiting.')
            return

        fpath = Path('APIs/{}/{}.yaml'.format(
            self.name, self.version
        ))
        if fpath.exists():
            logger.debug('{} already exists. Deleting..'.format(str(fpath)))
            fpath.unlink()
        # create the directory, if it doesn't exist
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()
        logger.info('Saving results to {}'.format(fpath))
        with fpath.open('w+') as outfile:
            yaml.dump(yaml_data, outfile, default_flow_style=False)

    def pull_links(self, result):
        g_links = html.fromstring(result.content).iterlinks()
        links, last = [], None
        for link in g_links:
            url = link[2].replace('../', '')
            if ('/' in url[len(self.base_path):] and link[0].text
                and url != last):
                links.append((link[0].text, url))
                last = url
        return links

    def scrape_content(self, content):
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

    def explore(self):
        if 'apidoc/' not in self.base_path:
            logger.warning('I don\'t know how to explore that yet.')
            return
        result = requests.get(self.host_url + self.base_path, verify=False)
        if not result:
            logger.warning("I couldn't find anything useful at {}.".format(
                self.host_url + self.base_path))
            return
        self.base_path = self.base_path.replace('.html', '')  # for next strep
        logger.info('Starting to explore {}{}'.format(self.host_url, self.base_path))
        links = self.pull_links(result)
        logger.debug('Found {} links!'.format(len(links)))
        self._visit_links(links)
        # sort the results by link name, to normalize return order
        self._queue = sorted(self._queue, key=lambda x: x[0][1])
        self._link_params()
