import hashlib
from database import CursorFromConnectionPool, DatabaseError


class User:
    """This class represents a user in our application.
    
    It handles user authentication, registration, and game management.
    """
    def __init__(self, username, email, password, id=None):
        """Create a new User object.
        
        Args:
            username: The user's username for login
            email: The user's email address
            password: The user's password (will be hashed before storing)
            id: The user's database ID (None for new users)
        """
        self.password_hash = None
        self.id = id
        self.username = username
        self.email = email
        self.password = password

    def save_to_db(self):
        """Save the user to the database.
        
        This will hash the password before saving.
        
        Returns:
            The user's database ID
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
        """Find a user by their username.
        
        Args:
            username: The username to search for
            
        Returns:
            A User object if found, None otherwise
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
        """Find a user by their database ID.
        
        Args:
            user_id: The database ID to search for
            
        Returns:
            A User object if found, None otherwise
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
        """Check if a password matches this user's password.
        
        Args:
            password_to_check: The password to verify
            
        Returns:
            True if the password matches, False otherwise
        """
        return self._hash_password(password_to_check) == self.password_hash

    @staticmethod
    def _hash_password(password):
        """Hash a password using SHA-256.
        
        Args:
            password: The password to hash
            
        Returns:
            The hashed password as a hexadecimal string
        """
        # Simple hashing for demonstration - in a real app, use a proper password hashing library like bcrypt
        return hashlib.sha256(password.encode()).hexdigest()

    def get_saved_games(self):
        """Get all games saved by this user.
        
        Returns:
            A list of Game objects saved by this user
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
        """Save a game to this user's collection.
        
        Args:
            game_id: The database ID of the game to save
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO user_saved_games (user_id, game_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                           (self.id, game_id))
                           
    def unsave_game(self, game_id):
        """Remove a game from this user's collection.
        
        Args:
            game_id: The database ID of the game to remove
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('DELETE FROM user_saved_games WHERE user_id = %s AND game_id = %s',
                           (self.id, game_id))