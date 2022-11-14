from pydantic import BaseSettings  # pragma: no cover
import boto3


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


def get_aws_creds():
    session = boto3.Session(
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_arn,
    )
    client = session.client("redshift")
    try:
        return client.get_cluster_credentials(
            DbUser=settings.db_user,
            ClusterIdentifier=settings.db_cluster_identifier,
        )

    except Exception as error:
        print(f"Unable to get credentials due to {error}")
