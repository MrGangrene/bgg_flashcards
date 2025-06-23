import psycopg2
from psycopg2 import pool


class DatabaseError(Exception):
    """Custom exception for database connection errors."""
    pass


class Database:
    """This class handles our database connections.
    It creates a connection pool so we can reuse connections.
    """
    _connection_pool = None
    _connection_error = None

    @classmethod
    def initialize(cls, minconn=1, maxconn=10, **kwargs):
        """This method sets up our connection pool.
        
        Args:
            minconn: The minimum number of connections to keep open
            maxconn: The maximum number of connections allowed
            **kwargs: Extra arguments to pass to the database connection
            
        Returns:
            bool: True if connection was successful, False otherwise
        
        Raises:
            DatabaseError: If connection to the database fails
        """
        try:
            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn,
                maxconn,
                **kwargs
            )
            cls._connection_error = None
            
            # Test the connection with a simple query
            with cls.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    
            return True
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            cls._connection_error = str(e)
            raise DatabaseError(f"Failed to connect to database: {str(e)}")
    
    @classmethod
    def get_connection_error(cls):
        """Get the last connection error message.
        
        Returns:
            str: The last connection error message or None if no error
        """
        return cls._connection_error

    @classmethod
    def get_connection(cls):
        """Get a connection from the pool.
        
        Returns:
            A database connection we can use
            
        Raises:
            DatabaseError: If the connection pool is not initialized
        """
        if cls._connection_pool is None:
            raise DatabaseError("Database connection pool not initialized")
        return cls._connection_pool.getconn()

    @classmethod
    def return_connection(cls, connection):
        """Put a connection back in the pool when we're done.
        
        Args:
            connection: The connection to return
        """
        if cls._connection_pool is not None:
            cls._connection_pool.putconn(connection)

    @classmethod
    def close_all_connections(cls):
        """Close all connections in the pool.
        This should be called when the program exits.
        """
        if cls._connection_pool is not None:
            cls._connection_pool.closeall()


class CursorFromConnectionPool:
    """This class helps us use database connections safely.
    It gets a connection from the pool and returns it when done.
    Use it with 'with' statements for automatic cleanup.
    """
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """Get a connection and cursor when entering a with block.
        
        Returns:
            A database cursor we can use for queries
            
        Raises:
            DatabaseError: If a database connection cannot be established
        """
        try:
            self.conn = Database.get_connection()
            self.cursor = self.conn.cursor()
            return self.cursor
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            Database._connection_error = str(e)
            raise DatabaseError(f"Failed to get database connection: {str(e)}")

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Clean up when exiting a with block.
        If there was an error, roll back changes.
        Otherwise, commit changes and close cursor.
        
        Args:
            exception_type: Type of exception if one occurred
            exception_value: The exception object if one occurred
            exception_traceback: The traceback if an exception occurred
        """
        if self.conn is None:
            return
            
        if exception_value:
            self.conn.rollback()
        else:
            if self.cursor:
                self.cursor.close()
            self.conn.commit()
        Database.return_connection(self.conn)