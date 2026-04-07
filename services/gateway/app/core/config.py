"""Gateway configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    postgres_user: str = "aerofly"
    postgres_password: str = "changeme"
    postgres_db: str = "aerofly"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # JWT
    jwt_secret: str = "changeme_jwt_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Services
    data_ingestion_url: str = "http://data-ingestion:8001"
    search_url: str = "http://search:8002"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
