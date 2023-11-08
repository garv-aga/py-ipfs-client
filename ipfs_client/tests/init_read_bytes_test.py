import io
import os

from ipfs_client.main import AsyncIPFSClientSingleton
from ipfs_client.settings.data_models import ConnectionLimits
from ipfs_client.settings.data_models import ExternalAPIAuth
from ipfs_client.settings.data_models import IPFSConfig
from ipfs_client.settings.data_models import IPFSWriterRateLimit
from ipfs_client.settings.data_models import RemotePinningConfig


# run this test as:
# IPFS_URL=https://ipfs.infura.io:5001 IPFS_AUTH_API_KEY=your_api_key
# IPFS_AUTH_API_SECRET=your_api_secret poetry run python -m
# ipfs_client.tests.init_read_bytes_test /path/to/binary/file


async def test_upload_read_binary(binary_file_path):
    ipfs_url = os.getenv('IPFS_URL', 'http://localhost:5001')
    ipfs_auth_api_key = os.getenv('IPFS_AUTH_API_KEY', None)
    ipfs_auth_api_secret = os.getenv('IPFS_AUTH_API_SECRET', None)
    ipfs_client_settings = IPFSConfig(
        url=ipfs_url,
        reader_url=ipfs_url,
        write_rate_limit=IPFSWriterRateLimit(
            req_per_sec=10, burst=10,   # 10 requests per second, burst 10
        ),  # 10 requests per second, burst 10
        timeout=60,
        local_cache_path='/tmp/ipfs_cache',
        connection_limits=ConnectionLimits(
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=60,
        ),
        remote_pinning=RemotePinningConfig(
            enabled=False,
            service_name='',
            service_endpoint='',
            service_token='',
        ),
    )
    if all([ipfs_auth_api_key, ipfs_auth_api_secret]):
        ipfs_client_settings.url_auth = ExternalAPIAuth(
            apiKey=ipfs_auth_api_key,
            apiSecret=ipfs_auth_api_secret,
        )
        ipfs_client_settings.reader_url_auth = ExternalAPIAuth(
            apiKey=ipfs_auth_api_key,
            apiSecret=ipfs_auth_api_secret,
        )
    ipfs_client = AsyncIPFSClientSingleton(
        settings=ipfs_client_settings,
    )
    await ipfs_client.init_sessions()
    file_contents = io.open(binary_file_path, 'rb').read()
    cid = await ipfs_client._ipfs_write_client.add_bytes(file_contents)
    print(cid)
    data = await ipfs_client._ipfs_read_client.cat(cid, bytes_mode=False)
    print(data)


if __name__ == '__main__':
    import asyncio
    import sys
    binary_file_upload_path = sys.argv[1]
    asyncio.run(test_upload_read_binary(binary_file_upload_path))
