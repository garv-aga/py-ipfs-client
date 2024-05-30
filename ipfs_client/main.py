import json
import asyncio
import httpx
from datetime import datetime, timedelta
from urllib.parse import urljoin

from httpx import AsyncClient
from httpx import AsyncHTTPTransport
from httpx import Limits
from httpx import Timeout
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import ipfs_client.exceptions
import ipfs_client.utils.addr as addr_util
from ipfs_client.dag import DAGSection
from ipfs_client.dag import IPFSAsyncClientError
from ipfs_client.default_logger import logger
from ipfs_client.settings.data_models import IPFSConfig


class AsyncIPFSClient:
    _settings: IPFSConfig
    _client: AsyncClient
    _scheduler: AsyncIOScheduler

    def __init__(
            self,
            addr,
            settings: IPFSConfig,
            api_base='api/v0',
            write_mode=False,

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
        self._write_mode = write_mode
        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()

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

        if self._settings.remote_pinning.enabled and self._write_mode:
            # checking if service_name, service_endpoint, and service_token are
            # set, if not, raise an error
            if not all(
                    [
                        self._settings.remote_pinning.service_name,
                        self._settings.remote_pinning.service_endpoint,
                        self._settings.remote_pinning.service_token,
                    ],
            ):
                raise ValueError(
                    'Remote pinning enabled but service_name, service_endpoint, or service_token not set',
                )

            # curl -X POST "http://127.0.0.1:5001/api/v0/pin/remote/service/add?arg=<service>&arg=<endpoint>&arg=<key>"
            # enable remote pinning service
            r = await self._client.post(
                url=f'/pin/remote/service/add?arg={self._settings.remote_pinning.service_name}&arg={self._settings.remote_pinning.service_endpoint}&arg={self._settings.remote_pinning.service_token}',
            )
            if r.status_code != 200:
                if r.status_code == 500:
                    # check for {"Message":"service already present","Code":0,"Type":"error"}
                    try:
                        resp = json.loads(r.text)
                    except json.JSONDecodeError:
                        raise IPFSAsyncClientError(
                            f'IPFS client error: remote pinning service add operation, response:{r}',
                        )
                    else:
                        if resp['Message'] == 'service already present':
                            self._logger.debug(
                                'Remote pinning service already present',
                            )
                            pass
                        else:
                            raise IPFSAsyncClientError(
                                f'IPFS client error: remote pinning service add operation, response:{r}',
                            )
                else:
                    raise IPFSAsyncClientError(
                        f'IPFS client error: remote pinning service add operation, response:{r}',
                    )
            else:
                self._logger.debug(
                    'Remote pinning service added successfully',
                )

        self.dag = DAGSection(self._client)
        self._logger.debug('Inited IPFS client on base url {}', self._base_url)

    async def add_str(self, string, **kwargs):
        try: 
            string_data = string.encode('utf-8')
        except Exception as e:
            raise e
        
        cid = await self.add_bytes(string_data, **kwargs)
        return cid
    
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
            resp = json.loads(r.text)
        except json.JSONDecodeError:
            return r.text
        else:
            generated_cid = resp['Hash']

        if self._settings.remote_pinning.enabled:
            # curl -X POST "http://127.0.0.1:5001/api/v0/pin/remote/add?arg=<ipfs-path>&service=<value>&name=<value>&background=false"
            # pin to remote pinning service
            r = await self._client.post(
                url=f'/pin/remote/add?arg={generated_cid}&service={self._settings.remote_pinning.service_name}&background={self._settings.remote_pinning.background_pinning}',
            )
            if r.status_code != 200:
                self._logger.error(
                    f'IPFS client error: remote pinning add operation, response:{r}',
                )

        unpin_delay = 12  # 7 days
        await self.schedule_archive_and_unpin(generated_cid, files, unpin_delay)
        return generated_cid

    async def add_json(self, json_obj, **kwargs):
        try:
            json_data = json.dumps(json_obj).encode('utf-8')
        except Exception as e:
            raise e

        cid = await self.add_bytes(json_data, **kwargs)
        return cid

    async def cat(self, cid, **kwargs):
        bytes_mode = kwargs.get('bytes_mode', False)
        if not bytes_mode:
            response_body = ''
        else:
            response_body = b''
        last_response_code = None
        async with self._client.stream(method='POST', url=f'/cat?arg={cid}') as response:
            if response.status_code != 200:
                raise IPFSAsyncClientError(
                    f'IPFS client error: cat on CID {cid}, response status code error: {response.status_code}',
                )
            if not bytes_mode:
                async for chunk in response.aiter_text():
                    response_body += chunk
            else:
                async for chunk in response.aiter_bytes():
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

    # Unpin the data using cid
    async def unpin(self, cid: str):
        print("Unpinning from IPFS ....")
        r = await self._client.post(
        url=f'/pin/rm?arg={cid}',
        )
        if r.status_code != 200:
            self._logger.error(
                f'IPFS client error: remote remove pin operation, response:{r}',
            )
        else:
            self._logger.info(f"Successfully unpinned {cid}")

    # Archive the data to Filecoin via Lighthouse PoDSI, make take up to two days for getting a deal
    async def archive(self, file: dict[str, bytes]):
        print("Archiving to Filecoin started ....")
        url = "https://node.lighthouse.storage/api/v0/add"
        headers = {'Authorization': f'Bearer YOUR_API_KEY'}
        files = file
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, files=files)
        if r.status_code != 200:
            self._logger.error(
                f'Lighthouse upload error, response:{r}',
            )
        try:
            resp = r.json()
        except json.JSONDecodeError:
            return r.text
        else:
            archived_cid = resp['Hash']
            self._logger.info(f'Archived CID: {archived_cid}')
            return archived_cid

    # Retrieve the data using Filecoin's native Lassie
    # Port number: 36711 might change as per your lassie daemon
    async def retrieve(self, cid, outputfname):
        url = f'http://127.0.0.1:36711/ipfs/{cid}?filename={outputfname}'
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            if r.status_code != 200:
                self._logger.error(
                    f'Lassie retrieve error, response:{r}',
                )
            with open(outputfname, 'wb') as f:
                f.write(r.content)
        self._logger.info(f"Successfully retrieved and saved file {outputfname}")
    
    async def schedule_archive_and_unpin(self, cid, file, delay):
        await asyncio.sleep(delay)
        #await self.archive(file)
        await self.unpin(cid)

    # Get prrof that you file was actually uploaded to the Filecoin network (PoDSI)
    async def get_proof(self, cid):
        url = f'https://api.lighthouse.storage/api/lighthouse/get_proof?cid={cid}&network=testnet'
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
        if r.status_code != 200:
            self._logger.error(
                f'Proof retrieve error, response:{r}',
            )
        else:
            return r.json()
class AsyncIPFSClientSingleton:
    def __init__(self, settings: IPFSConfig):
        self._ipfs_write_client = AsyncIPFSClient(
            addr=settings.url, settings=settings, write_mode=True,
        )
        self._ipfs_read_client = AsyncIPFSClient(
            addr=settings.reader_url, settings=settings, write_mode=False,
        )
        self._initialized = False

    async def init_sessions(self):
        if self._initialized:
            return
        await self._ipfs_write_client.init_session()
        await self._ipfs_read_client.init_session()
        self._initialized = True
