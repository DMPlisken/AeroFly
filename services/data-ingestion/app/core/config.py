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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
