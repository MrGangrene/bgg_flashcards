import psycopg2
from psycopg2 import pool


class Database:
    _connection_pool = None

    @classmethod
    def initialize(cls, minconn=1, maxconn=10, **kwargs):
        cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn,
            maxconn,
            **kwargs
        )

    @classmethod
    def get_connection(cls):
        return cls._connection_pool.getconn()

    @classmethod
    def return_connection(cls, connection):
        cls._connection_pool.putconn(connection)

    @classmethod
    def close_all_connections(cls):
        cls._connection_pool.closeall()


class CursorFromConnectionPool:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = Database.get_connection()
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if exception_value:
            self.conn.rollback()
        else:
            self.cursor.close()
            self.conn.commit()
        Database.return_connection(self.conn)