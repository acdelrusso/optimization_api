from pydantic import BaseSettings  # pragma: no cover


class Settings(BaseSettings):  # pragma: no cover
    db_endpoint: str
    db_port: str
    db_region: str
    db_name: str
    db_cluster_identifier: str
    db_user: str
    secret_arn: str
    access_key_id: str

    class Config:
        env_file = "./src/.env"


settings = Settings()  # pragma: no cover
