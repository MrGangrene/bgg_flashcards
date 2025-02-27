import hashlib
from database import CursorFromConnectionPool


class User:
    def __init__(self, username, email, password, id=None):
        self.password_hash = None
        self.id = id
        self.username = username
        self.email = email
        self.password = password

    def save_to_db(self):
        with CursorFromConnectionPool() as cursor:
            # Hash the password before saving
            password_hash = self._hash_password(self.password)

            cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id',
                           (self.username, self.email, password_hash))
            self.id = cursor.fetchone()[0]
            return self.id

    @classmethod
    def load_by_username(cls, username):
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
        return self._hash_password(password_to_check) == self.password_hash

    @staticmethod
    def _hash_password(password):
        # Simple hashing for demonstration - in a real app, use a proper password hashing library like bcrypt
        return hashlib.sha256(password.encode()).hexdigest()

    def get_saved_games(self):
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
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO user_saved_games (user_id, game_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                           (self.id, game_id))
                           
    def unsave_game(self, game_id):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('DELETE FROM user_saved_games WHERE user_id = %s AND game_id = %s',
                           (self.id, game_id))