import os
import asyncio
from ipfs_client.main import AsyncIPFSClientSingleton
from ipfs_client.settings.data_models import ConnectionLimits, ExternalAPIAuth, IPFSConfig, IPFSWriterRateLimit, RemotePinningConfig

# run this test as:
# IPFS_URL=https://ipfs.infura.io:5001 IPFS_AUTH_API_KEY=your_api_key
# IPFS_AUTH_API_SECRET=your_api_secret poetry run python -m
# ipfs_client.tests.init_archive_and_unpin_test

async def test_archive_and_unpin():
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
    cid = await ipfs_client._ipfs_write_client.add_json({'test': 'archive and unpin'})
    delay = 12
    await asyncio.sleep(delay + 5) # This much delay might not me sufficient, as it can sometimes take hours to generate the proof
    pinned_cids = await ipfs_client._ipfs_write_client._client.post('/pin/ls')
    pinned_cids = pinned_cids.json()['Keys']
    assert cid not in pinned_cids, f"CID {cid} should have been unpinned"

    print(f"Successfully unpinned CID: {cid}")

if __name__ == '__main__':
    asyncio.run(test_archive_and_unpin())
