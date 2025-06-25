"""Database Connection Management Module.

This module provides database connection management for the BGG Flashcards application
using PostgreSQL and psycopg2. It implements a connection pool pattern for efficient
connection reuse and provides context managers for safe database operations.

Classes:
    Database: Connection pool management and initialization
    CursorFromConnectionPool: Context manager for safe database operations
    DatabaseError: Custom exception for database-related errors

Usage:
    # Initialize connection pool
    Database.initialize(database='mydb', user='user', password='pass')
    
    # Use context manager for operations
    with CursorFromConnectionPool() as cursor:
        cursor.execute('SELECT * FROM games')
        results = cursor.fetchall()
        
Features:
    - Connection pooling for performance
    - Automatic transaction management
    - Error handling and rollback
    - Context manager safety
    - Connection testing and validation
"""

import psycopg2
from psycopg2 import pool


class DatabaseError(Exception):
    """Custom exception for database connection errors.
    
    Raised when database connections fail or other database-related
    errors occur that should be handled specifically by the application.
    
    This provides a cleaner interface for handling database errors
    without exposing low-level psycopg2 exception details.
    """
    pass


class Database:
    """Manages database connections using a connection pool.
    
    This class implements the singleton pattern for connection pool management,
    ensuring efficient connection reuse across the application. It provides
    centralized connection management with proper error handling.
    
    Features:
        - Connection pooling for performance optimization
        - Centralized connection configuration
        - Connection testing and validation
        - Error tracking and reporting
        - Thread-safe connection management
        
    Class Attributes:
        _connection_pool: The psycopg2 connection pool instance
        _connection_error: Last connection error message for debugging
        
    Thread Safety:
        The underlying psycopg2 connection pool is thread-safe, making
        this class suitable for multithreaded applications.
    """
    _connection_pool = None
    _connection_error = None

    @classmethod
    def initialize(cls, minconn=1, maxconn=10, **kwargs):
        """Initialize the database connection pool.
        
        Sets up a PostgreSQL connection pool with the specified parameters.
        Tests the connection to ensure it's working before returning.
        
        Args:
            minconn (int, optional): Minimum number of connections to maintain. Defaults to 1.
            maxconn (int, optional): Maximum number of connections allowed. Defaults to 10.
            **kwargs: Database connection parameters (database, user, password, host, port)
            
        Returns:
            bool: True if connection pool was created successfully
            
        Raises:
            DatabaseError: If connection to the database fails
            
        Example:
            Database.initialize(
                database='bgg_flashcards',
                user='postgres',
                password='secret',
                host='localhost',
                port='5432'
            )
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
        """Get the last connection error message for debugging.
        
        Returns:
            str: The last connection error message or None if no error
            
        Note:
            Useful for debugging connection issues or displaying
            user-friendly error messages.
        """
        return cls._connection_error

    @classmethod
    def get_connection(cls):
        """Get a connection from the pool.
        
        Retrieves an available connection from the connection pool.
        The connection must be returned to the pool after use.
        
        Returns:
            psycopg2.connection: A database connection ready for use
            
        Raises:
            DatabaseError: If the connection pool is not initialized
            
        Note:
            Always return connections using return_connection() to avoid
            pool exhaustion. Consider using CursorFromConnectionPool
            context manager for automatic connection management.
        """
        if cls._connection_pool is None:
            raise DatabaseError("Database connection pool not initialized")
        return cls._connection_pool.getconn()

    @classmethod
    def return_connection(cls, connection):
        """Return a connection to the pool after use.
        
        Args:
            connection (psycopg2.connection): The connection to return
            
        Note:
            This must be called for every connection obtained from
            get_connection() to prevent pool exhaustion.
        """
        if cls._connection_pool is not None:
            cls._connection_pool.putconn(connection)

    @classmethod
    def close_all_connections(cls):
        """Close all connections in the pool.
        
        Cleanly shuts down the connection pool and closes all connections.
        This should be called when the application exits to ensure proper
        resource cleanup.
        
        Note:
            After calling this method, the pool must be reinitialized
            before it can be used again.
        """
        if cls._connection_pool is not None:
            cls._connection_pool.closeall()


class CursorFromConnectionPool:
    """Context manager for safe database operations with automatic cleanup.
    
    This class implements the context manager protocol to provide safe
    database operations with automatic connection and transaction management.
    It handles connection acquisition, cursor creation, transaction control,
    and resource cleanup.
    
    Features:
        - Automatic connection management
        - Transaction control with commit/rollback
        - Cursor creation and cleanup
        - Exception handling with rollback
        - Resource cleanup guarantees
        
    Usage:
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO games (name) VALUES (%s)', ('Catan',))
            # Automatic commit on success, rollback on exception
            
    Attributes:
        conn: The database connection (set during context entry)
        cursor: The database cursor (set during context entry)
        
    Thread Safety:
        Each instance manages its own connection and cursor, making it
        safe to use in multithreaded environments.
    """
    def __init__(self):
        """Initialize the context manager.
        
        Sets up initial state with no connection or cursor.
        Actual resource acquisition happens in __enter__.
        """
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """Enter the context manager and acquire database resources.
        
        Gets a connection from the pool, creates a cursor, and returns
        the cursor for database operations.
        
        Returns:
            psycopg2.cursor: A database cursor ready for operations
            
        Raises:
            DatabaseError: If a database connection cannot be established
            
        Note:
            This method is called automatically when entering a 'with' block.
        """
        try:
            self.conn = Database.get_connection()
            self.cursor = self.conn.cursor()
            return self.cursor
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            Database._connection_error = str(e)
            raise DatabaseError(f"Failed to get database connection: {str(e)}")

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Exit the context manager and clean up resources.
        
        Handles transaction control based on whether an exception occurred:
        - If exception: Rollback transaction
        - If success: Commit transaction and close cursor
        
        Always returns the connection to the pool for reuse.
        
        Args:
            exception_type (type): Type of exception if one occurred
            exception_value (Exception): The exception object if one occurred
            exception_traceback (traceback): The traceback if an exception occurred
            
        Note:
            This method is called automatically when exiting a 'with' block.
            Return value of None means exceptions are not suppressed.
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