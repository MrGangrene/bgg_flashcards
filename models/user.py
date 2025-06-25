"""User Model Module.

This module contains the User class which handles user authentication,
registration, and user-specific data management.

The User class provides functionality for:
- User registration and authentication
- Password hashing and verification
- User game collection management
- Database CRUD operations for user data

Security Note:
    The current implementation uses SHA-256 for password hashing.
    For production use, consider upgrading to bcrypt or similar
    password hashing libraries for enhanced security.
"""

import hashlib
from database import CursorFromConnectionPool, DatabaseError


class User:
    """Represents a user in the BGG Flashcards application.
    
    This class handles user authentication, registration, and personal game
    collection management. Each user can save games to their collection
    and create flashcards for those games.
    
    Attributes:
        id (int): Database primary key
        username (str): Unique username for login
        email (str): User's email address
        password (str): Plain text password (only used during registration)
        password_hash (str): Hashed password stored in database
        
    Security:
        - Passwords are hashed using SHA-256 before storage
        - Plain text passwords are never stored in the database
        - Password verification is done by comparing hashes
        
    Database Relations:
        - One-to-many with flashcards (user can create multiple flashcards)
        - Many-to-many with games through user_saved_games table
    """
    def __init__(self, username, email, password, id=None):
        """Initialize a new User instance.
        
        Args:
            username (str): The user's unique username for login
            email (str): The user's email address
            password (str): The user's password (will be hashed before storing)
            id (int, optional): The user's database ID (None for new users)
            
        Note:
            The password is stored in plain text temporarily and should be
            hashed immediately using save_to_db() or similar operations.
        """
        self.password_hash = None
        self.id = id
        self.username = username
        self.email = email
        self.password = password

    def save_to_db(self):
        """Save the user to the database with hashed password.
        
        Hashes the plain text password and stores the user record in the database.
        The user's ID will be set to the new database primary key.
        
        Returns:
            int: The user's database ID
            
        Raises:
            DatabaseError: If database operation fails or username already exists
            
        Security:
            The plain text password is hashed using SHA-256 before storage.
            The original password is not stored in the database.
        """
        with CursorFromConnectionPool() as cursor:
            # Hash the password before saving
            password_hash = self._hash_password(self.password)

            cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id',
                           (self.username, self.email, password_hash))
            self.id = cursor.fetchone()[0]
            return self.id

    @classmethod
    def load_by_username(cls, username):
        """Load a user from the database by username.
        
        Args:
            username (str): The username to search for
            
        Returns:
            User: User object if found, None otherwise
            
        Note:
            The returned User object will have an empty password field
            but will contain the password_hash for verification purposes.
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT id, username, email, password_hash FROM users WHERE username = %s', (username,))
            user_data = cursor.fetchone()
            if user_data:
                id, username, email, password_hash = user_data
                user = cls(username, email, '', id)
                user.password_hash = password_hash
                return user
            return None
            
    @classmethod
    def load_by_id(cls, user_id):
        """Load a user from the database by ID.
        
        Args:
            user_id (int): The database ID to search for
            
        Returns:
            User: User object if found, None otherwise
            
        Note:
            The returned User object will have an empty password field
            but will contain the password_hash for verification purposes.
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT id, username, email, password_hash FROM users WHERE id = %s', (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                id, username, email, password_hash = user_data
                user = cls(username, email, '', id)
                user.password_hash = password_hash
                return user
            return None

    def verify_password(self, password_to_check):
        """Verify if a password matches this user's stored password.
        
        Hashes the provided password and compares it with the stored
        password hash for secure authentication.
        
        Args:
            password_to_check (str): The password to verify
            
        Returns:
            bool: True if the password matches, False otherwise
            
        Security:
            Uses the same SHA-256 hashing algorithm used during registration
            to ensure consistent password verification.
        """
        return self._hash_password(password_to_check) == self.password_hash

    @staticmethod
    def _hash_password(password):
        """Hash a password using SHA-256.
        
        Args:
            password (str): The password to hash
            
        Returns:
            str: The hashed password as a hexadecimal string
            
        Security Note:
            This implementation uses SHA-256 for demonstration purposes.
            For production applications, consider using bcrypt, scrypt, or
            argon2 which are specifically designed for password hashing
            and include built-in salt generation and configurable work factors.
        """
        # Simple hashing for demonstration - in a real app, use a proper password hashing library like bcrypt
        return hashlib.sha256(password.encode()).hexdigest()

    def get_saved_games(self):
        """Get all games in this user's personal collection.
        
        Retrieves all games that the user has saved to their collection
        through the user_saved_games relationship table.
        
        Returns:
            list[Game]: List of Game objects saved by this user
            
        Note:
            The returned Game objects contain basic information (name, rating,
            player counts, image) but not all detailed BGG data. Use
            Game.load_by_id() if full details are needed.
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                SELECT g.id, g.name, g.avg_rating, g.min_players, g.max_players, g.image_path
                FROM games g
                JOIN user_saved_games usg ON g.id = usg.game_id
                WHERE usg.user_id = %s
            ''', (self.id,))

            from models.game import Game
            games = []
            for game_data in cursor.fetchall():
                game_id, name, avg_rating, min_players, max_players, image_path = game_data
                game = Game(name, avg_rating, min_players, max_players, image_path, game_id)
                games.append(game)

            return games

    def save_game(self, game_id):
        """Add a game to this user's personal collection.
        
        Creates a relationship between the user and game in the
        user_saved_games table. Uses ON CONFLICT DO NOTHING to
        prevent duplicate entries.
        
        Args:
            game_id (int): The database ID of the game to save
            
        Note:
            If the game is already in the user's collection, this
            operation will silently succeed without creating duplicates.
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO user_saved_games (user_id, game_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                           (self.id, game_id))
                           
    def unsave_game(self, game_id):
        """Remove a game from this user's personal collection.
        
        Removes the relationship between the user and game from the
        user_saved_games table. Does not delete the game itself or
        any associated flashcards.
        
        Args:
            game_id (int): The database ID of the game to remove
            
        Note:
            This only removes the game from the user's collection.
            Flashcards created by the user for this game will remain
            in the database and can still be accessed if the user
            re-saves the game.
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('DELETE FROM user_saved_games WHERE user_id = %s AND game_id = %s',
                           (self.id, game_id))