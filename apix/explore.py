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
from logzero import logger
from pathlib import Path
from apix.parsers import apipie



@attr.s()
class AsyncExplorer():
    name = attr.ib(default=None)
    version = attr.ib(default=None)
    host_url = attr.ib(default=None)
    base_path = attr.ib(default=None)
    parser = attr.ib(default=None)
    _data = attr.ib(default={}, repr=False)
    _queue = attr.ib(default=[], repr=False)

    def __attrs_post_init__(self):
        if not self.version:
            self.version = time.strftime('%Y-%m-%d', time.localtime())
        # choose the correct parser class from known parsers
        if self.parser.lower() == 'apipie':
            self.parser = apipie.APIPie()
        if not self.parser or isinstance(self.parser, str):
            logger.warning('No known parser specified! Please review documentation.')

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
            logger.debug(f'Scraping {link[1]}')
            self._data[link[1]] = self.parser.scrape_content(content)

    def save_data(self):
        yaml_data = self.parser.yaml_format(self._data)
        if not yaml_data:
            logger.warning('No data to be saved. Exiting.')
            return

        fpath = Path(f'APIs/{self.name}/{self.version}.yaml')
        if fpath.exists():
            logger.warning(f'{fpath} already exists. Deleting..')
            fpath.unlink()
        # create the directory, if it doesn't exist
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()
        logger.info(f'Saving results to {fpath}')
        with fpath.open('w+') as outfile:
            yaml.dump(yaml_data, outfile, default_flow_style=False)

    def explore(self):
        if 'apidoc/' not in self.base_path:
            logger.warning('I don\'t know how to explore that yet.')
            return
        result = requests.get(self.host_url + self.base_path, verify=False)
        if not result:
            logger.warning(f"I couldn't find anything useful at "
                           f"{self.host_url}{self.base_path}.")
            return
        self.base_path = self.base_path.replace('.html', '')  # for next strep
        logger.info(f'Starting to explore {self.host_url}{self.base_path}')
        links = self.parser.pull_links(result, self.base_path)
        logger.debug(f'Found {len(links)} links!')
        self._visit_links(links)
        # sort the results by link name, to normalize return order
        self._queue = sorted(self._queue, key=lambda x: x[0][1])
        self._link_params()
