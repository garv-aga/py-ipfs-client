import json
from urllib.parse import urljoin

from httpx import AsyncClient
from httpx import AsyncHTTPTransport
from httpx import Limits
from httpx import Timeout

import ipfs_client.exceptions
import ipfs_client.utils.addr as addr_util
from ipfs_client.dag import DAGSection
from ipfs_client.dag import IPFSAsyncClientError
from ipfs_client.default_logger import logger
from ipfs_client.settings.data_models import IPFSConfig


class AsyncIPFSClient:
    _settings: IPFSConfig
    _client: AsyncClient

    def __init__(
            self,
            addr,
            settings: IPFSConfig,
            api_base='api/v0',

    ):
        try:
            self._base_url, \
                self._host_numeric = addr_util.multiaddr_to_url_data(
                    addr, api_base,
                )
        except ipfs_client.exceptions.AddressError:
            if not addr_util.is_valid_url(addr):
                raise ValueError('Invalid IPFS address')
            self._base_url = urljoin(addr, api_base)
            self._host_numeric = addr_util.P_TCP
        self.dag = None
        self._logger = logger.bind(module='IPFSAsyncClient')
        self._settings = settings

    async def init_session(self):
        conn_limits = self._settings.connection_limits
        self._async_transport = AsyncHTTPTransport(
            limits=Limits(
                max_connections=conn_limits.max_connections,
                max_keepalive_connections=conn_limits.max_connections,
                keepalive_expiry=conn_limits.keepalive_expiry,
            ),
        )
        client_init_args = dict(
            base_url=self._base_url,
            timeout=Timeout(self._settings.timeout),
            follow_redirects=False,
            transport=self._async_transport,
        )
        if self._settings.url_auth:
            client_init_args.update(
                {
                    'auth': (
                        self._settings.url_auth.apiKey,
                        self._settings.url_auth.apiSecret,
                    ),
                },
            )
        self._client = AsyncClient(**client_init_args)
        self.dag = DAGSection(self._client)
        self._logger.debug('Inited IPFS client on base url {}', self._base_url)

    def add_str(self, string, **kwargs):
        # TODO
        pass

    async def add_bytes(self, data: bytes, **kwargs):
        files = {'': data}
        r = await self._client.post(
            url='/add?cid-version=1',
            files=files,
        )
        if r.status_code != 200:
            raise IPFSAsyncClientError(
                f'IPFS client error: add_bytes operation, response:{r}',
            )

        try:
            return json.loads(r.text)
        except json.JSONDecodeError:
            return r.text

    async def add_json(self, json_obj, **kwargs):
        try:
            json_data = json.dumps(json_obj).encode('utf-8')
        except Exception as e:
            raise e

        cid = await self.add_bytes(json_data, **kwargs)
        return cid['Hash']

    async def cat(self, cid, **kwargs):
        response_body = ''
        last_response_code = None
        async with self._client.stream(method='POST', url=f'/cat?arg={cid}') as response:
            if response.status_code != 200:
                raise IPFSAsyncClientError(
                    f'IPFS client error: cat on CID {cid}, response status code error: {response.status_code}',
                )

            async for chunk in response.aiter_text():
                response_body += chunk
            last_response_code = response.status_code
        if not response_body:
            raise IPFSAsyncClientError(
                f'IPFS client error: cat on CID {cid}, response body empty. response status code error: {last_response_code}',
            )
        return response_body

    async def get_json(self, cid, **kwargs):
        json_data = await self.cat(cid)
        try:
            return json.loads(json_data)
        except json.JSONDecodeError:
            return json_data


class AsyncIPFSClientSingleton:
    def __init__(self, settings: IPFSConfig):
        self._ipfs_write_client = AsyncIPFSClient(
            addr=settings.url, settings=settings,
        )
        self._ipfs_read_client = AsyncIPFSClient(
            addr=settings.reader_url, settings=settings,
        )
        self._initialized = False

    async def init_sessions(self):
        if self._initialized:
            return
        await self._ipfs_write_client.init_session()
        await self._ipfs_read_client.init_session()
        self._initialized = True
