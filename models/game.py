from database import CursorFromConnectionPool


class Game:
    def __init__(self, name, avg_rating, min_players, max_players, image_path, id=None):
        self.id = id
        self.name = name
        self.avg_rating = avg_rating
        self.min_players = min_players
        self.max_players = max_players
        self.image_path = image_path

    def save_to_db(self):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                INSERT INTO games (name, avg_rating, min_players, max_players, image_path) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (self.name, self.avg_rating, self.min_players, self.max_players, self.image_path))
            self.id = cursor.fetchone()[0]
            return self.id

    @classmethod
    def load_by_id(cls, game_id):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT name, avg_rating, min_players, max_players, image_path FROM games WHERE id = %s',
                           (game_id,))
            game_data = cursor.fetchone()
            if game_data:
                name, avg_rating, min_players, max_players, image_path = game_data
                return cls(name, avg_rating, min_players, max_players, image_path, game_id)
            return None

    @classmethod
    def search_by_name(cls, name_query):
        with CursorFromConnectionPool() as cursor:
            cursor.execute(
                'SELECT id, name, avg_rating, min_players, max_players, image_path FROM games WHERE name ILIKE %s',
                (f'%{name_query}%',))
            games = []
            for game_data in cursor.fetchall():
                game_id, name, avg_rating, min_players, max_players, image_path = game_data
                games.append(cls(name, avg_rating, min_players, max_players, image_path, game_id))
            return games

    def get_flashcards(self):
        from models.flashcard import Flashcard
        return Flashcard.get_by_game_id(self.id)