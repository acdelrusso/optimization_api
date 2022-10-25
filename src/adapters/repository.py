from abc import ABC, abstractmethod
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
import src.config as config
from src.domain.models import Sku


class AbstractRepository(ABC):
    @abstractmethod
    def add(self, skus: list[Sku], scenario_name: str):
        pass

    def delete(self, scenario_name: str):
        pass

    def get(self, scenario_name: str):
        pass


class AWSRedshiftRepository(AbstractRepository):
    def __init__(self) -> None:
        session = boto3.Session(
            aws_access_key_id=config.settings.access_key_id,
            aws_secret_access_key=config.settings.secret_arn,
        )
        self.client = session.client("redshift")
        try:
            self.creds = self.client.get_cluster_credentials(
                DbUser=config.settings.db_user,
                ClusterIdentifier=config.settings.db_cluster_identifier,
            )
        except Exception as error:
            print(f"Unable to get credentials due to {error}")

        try:
            self.conn = psycopg2.connect(
                host=config.settings.db_endpoint,
                port=config.settings.db_port,
                database=config.settings.db_name,
                user=self.creds["DbUser"],
                password=self.creds["DbPassword"],
                cursor_factory=RealDictCursor,
            )
            self.cur = self.conn.cursor()
        except Exception as e:
            print(f"Unable to connect to DB due to {e}")

    def test_connection(self):
        self.cur.execute("""SELECT now()""")
        query_results = self.cur.fetchall()
        print(query_results)

    def add(self, skus, scenario_name: str):
        args_str = ",".join(
            self.cur.mogrify(
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (scenario_name, *sku)
            )
            for sku in skus
        )
        self.cur.execute(f"INSERT INTO table VALUES {args_str}")
        self.conn.commit()

    def delete(self, scenario_name: str):
        self.cur.execute(
            "DELETE * FROM table WHERE scenario_name == %s",
            scenario_name,
        )
        self.conn.commit()

    def get(self):
        self.cur.execute("SELECT DISCTINCT scenario_name FROM table")
        return self.cur.fetchall()


class Sqlite3Repository(AbstractRepository):
    def __init__(self, connection) -> None:
        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.conn = connection
        self.conn.row_factory = dict_factory

    def add(self, skus, scenario_name: str):
        print()
        for sku in skus:
            self.conn.execute(
                "INSERT INTO scenarios VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (scenario_name, *sku.to_tuple()),
            )

    def delete(self, scenario_name: str):
        self.conn.execute(
            "DELETE FROM scenarios WHERE scenario_name == ?", (scenario_name,)
        )

    def get_all(self) -> list:
        res = self.conn.execute("SELECT DISTINCT scenario_name FROM scenarios")
        return res.fetchall()

    def get(self, scenario_name: str):
        res = self.conn.execute(
            "SELECT * FROM scenarios WHERE scenario_name == ?", (scenario_name,)
        )
        return res.fetchall()

    def test_connection(self):
        res = self.conn.execute("""SELECT now()""")
        query_results = res.fetchall()
        print(query_results)
