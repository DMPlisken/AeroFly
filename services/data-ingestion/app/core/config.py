"""Data Ingestion configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str = "aerofly"
    postgres_password: str = "changeme"
    postgres_db: str = "aerofly"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    dfs_base_url: str = "https://aip.dfs.de"

    # The sidecar scraper container. Overridable via SCRAPER_URL env (set in
    # docker-compose.yml). Used by the sync pipeline to drive Playwright-
    # driven DFS scrapes.
    scraper_url: str = "http://scraper:8003"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    class Config:
        env_file = ".env"


settings = Settings()
