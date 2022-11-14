from abc import ABC, abstractmethod
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
import src.config as config


class AbstractRepository(ABC):
    @abstractmethod
    def add(self, table_name: str, data: dict):
        pass

    def delete(self, table_name: str, criteria: dict):
        pass

    def select(self, table_name: str, criteria: dict = None, order_by: str = None):
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

    def add(self, skus, scenario_name: str, strategy: str):
        args_str = ",".join(
            self.cur.mogrify(
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (strategy, scenario_name, *sku),
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

    def select(self):
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

    def __del__(self):
        self.conn.close()

    def _execute(self, statement: str, values=None):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(statement, values or [])
            return cursor

    def create_table(self, table_name: str, columns: dict):
        columns_with_types = [
            f"{column_name} {data_type}" for column_name, data_type in columns.items()
        ]
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name}
            ({', '.join(columns_with_types)});
            """
        )

    def add(self, table_name, data):
        placeholders = ", ".join("?" * len(data))
        column_names = ", ".join(data.keys())
        column_values = tuple(data.values())

        self._execute(
            f"""
            INSERT INTO {table_name}
            ({column_names})
            VALUES ({placeholders});
            """,
            column_values,
        )

    def delete(self, table_name: str, criteria: dict):
        placeholders = [f"{column} = ?" for column in criteria]
        delete_criteria = " AND ".join(placeholders)
        self._execute(
            f"""
            DELETE FROM {table_name}
            WHERE {delete_criteria};
            """,
            tuple(criteria.values()),
        )

    def select(
        self,
        table_name: str,
        fields: list[str] = None,
        criteria: dict = None,
        order_by: str = None,
        distinct: bool = False,
    ) -> list:
        criteria = criteria or {}

        fields = ", ".join(fields) if fields else "*"

        query = f"SELECT{' DISTINCT ' if distinct else ' '}{fields} FROM {table_name}"

        if criteria:
            placeholders = [f"{column} = ?" for column in criteria]
            select_criteria = " AND ".join(placeholders)
            query += f" WHERE {select_criteria}"

        if order_by:
            query += f" ORDER BY {order_by}"

        return self._execute(query, tuple(criteria.values()))
