from typing import Optional

from pydantic import BaseModel


class ConnectionLimits(BaseModel):
    max_connections: int = 100
    max_keepalive_connections: int = 50
    keepalive_expiry: int = 300


class IPFSWriterRateLimit(BaseModel):
    req_per_sec: int
    burst: int


class ExternalAPIAuth(BaseModel):
    # this is most likely used as a basic auth tuple of (username, password)
    apiKey: str
    apiSecret: str = ''


class RemotePinningConfig(BaseModel):
    enabled: bool
    service_name: Optional[str] = ""
    service_endpoint: Optional[str] = ""
    service_token: Optional[str] = ""
    background_pinning: Optional[bool] = False


class IPFSConfig(BaseModel):
    url: str
    url_auth: Optional[ExternalAPIAuth] = None
    reader_url: str
    reader_url_auth: Optional[ExternalAPIAuth] = None
    write_rate_limit: IPFSWriterRateLimit
    timeout: int
    local_cache_path: str
    connection_limits: ConnectionLimits
    remote_pinning: RemotePinningConfig
