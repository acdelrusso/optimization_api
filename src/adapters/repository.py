from abc import ABC, abstractmethod
import random


class AbstractRepository(ABC):
    @abstractmethod
    def add(self, table_name: str, data: dict):
        pass

    def add_many(self, table_name, src, scenario_name, skus: list[dict]):
        pass

    def delete(self, table_name: str, criteria: dict):
        pass

    def select(self, table_name: str, criteria: dict = None, order_by: str = None):
        pass


class PostgresRepository(AbstractRepository):
    def __init__(self, connection) -> None:
        self.conn = connection

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

    def add_many(self, table_name, src, scenario_name, skus: list[dict]):
        scenario_id = random.randint(1000000000, 9999999999)

        placeholders = "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
        column_names = ", ".join(skus[0].keys()) + ", src, scnr_desc, scnr_id"

        with self.conn.cursor() as cur:
            args_str = ",".join(
                cur.mogrify(
                    f"({placeholders})",
                    ((*sku.values(), str(src), str(scenario_name), str(scenario_id))),
                ).decode("utf-8")
                for sku in skus
            )

        self._execute(
            f"""
            INSERT INTO {table_name}
            ({column_names})
            VALUES {args_str}
            """
        )

    def add(self, table_name, data):
        placeholders = ", ".join("%s" * len(data))
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
        placeholders = [f"{column} = %s" for column in criteria]
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
            placeholders = [f"{column} = %s" for column in criteria]
            select_criteria = " AND ".join(placeholders)
            query += f" WHERE {select_criteria}"

        if order_by:
            query += f" ORDER BY {order_by}"

        return self._execute(query, tuple(criteria.values()))


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

    def _execute_many(self, statement, values):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.executemany(statement, values)
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

    def add_many(self, table_name, src, scenario_name, skus: list[dict]):
        iter_data = [(src, scenario_name, *sku.values()) for sku in skus]

        column_names = "src, scenario_name, " + ", ".join(skus[0].keys())

        print(iter_data)

        self._execute_many(
            f"""
            INSERT INTO {table_name}
            ({column_names})
            VALUES (?, ? ,? ,? ,? ,? ,?, ? ,? ,?, ? ,? ,? ,? ,? ,?);
            """,
            iter_data,
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
