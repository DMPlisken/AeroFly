"""Search service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    meili_host: str = "meilisearch"
    meili_port: int = 7700
    meili_master_key: str = "changeme_meili_key"

    data_ingestion_url: str = "http://data-ingestion:8001"

    @property
    def meili_url(self) -> str:
        return f"http://{self.meili_host}:{self.meili_port}"

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    class Config:
        env_file = ".env"


settings = Settings()
