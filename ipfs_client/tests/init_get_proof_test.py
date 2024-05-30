import os
import asyncio

from ipfs_client.main import AsyncIPFSClientSingleton
from ipfs_client.settings.data_models import ConnectionLimits
from ipfs_client.settings.data_models import ExternalAPIAuth
from ipfs_client.settings.data_models import IPFSConfig
from ipfs_client.settings.data_models import IPFSWriterRateLimit
from ipfs_client.settings.data_models import RemotePinningConfig

# run this test as:
# IPFS_URL=https://ipfs.infura.io:5001 IPFS_AUTH_API_KEY=your_api_key
# IPFS_AUTH_API_SECRET=your_api_secret poetry run python -m
# ipfs_client.tests.init_get_proof_test

async def test_get_proof():
    ipfs_url = os.getenv('IPFS_URL', 'http://localhost:5001')
    ipfs_auth_api_key = os.getenv('IPFS_AUTH_API_KEY', None)
    ipfs_auth_api_secret = os.getenv('IPFS_AUTH_API_SECRET', None)
    ipfs_client_settings = IPFSConfig(
        url=ipfs_url,
        reader_url=ipfs_url,
        write_rate_limit=IPFSWriterRateLimit(
            req_per_sec=10, burst=10,
        ),
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
    
    # Archive a file to Filecoin and get the CID
    file = {'file.txt': b'Get Proof!!'}
    archived_cid = await ipfs_client._ipfs_write_client.archive(file)

    await asyncio.sleep(10) # buffer

    # Call the get_proof method with the CID from the archive operation
    proof = await ipfs_client._ipfs_read_client.get_proof(archived_cid)

    # Verify that the proof is retrieved successfully
    if proof:
        print(f"Proof for CID {archived_cid}: {proof}")
    else:
        print(f"Failed to retrieve proof for CID {archived_cid}")

if __name__ == '__main__':
    asyncio.run(test_get_proof())
