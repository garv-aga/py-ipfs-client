from pydantic import BaseModel

class ConnectionLimits(BaseModel):
    max_connections: int = 100
    max_keepalive_connections: int = 50
    keepalive_expiry: int = 300


class IPFSWriterRateLimit(BaseModel):
    req_per_sec: int
    burst: int


class IPFSConfig(BaseModel):
    url: str
    reader_url: str
    write_rate_limit: IPFSWriterRateLimit
    timeout: int
    local_cache_path: str
    connection_limits: ConnectionLimits
