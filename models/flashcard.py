from database import CursorFromConnectionPool


class Flashcard:
    def __init__(self, game_id, user_id, category, title, content, id=None):
        self.id = id
        self.game_id = game_id
        self.user_id = user_id
        self.category = category
        self.title = title
        self.content = content

    def save_to_db(self):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                INSERT INTO flashcards (game_id, user_id, category, title, content) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (self.game_id, self.user_id, self.category, self.title, self.content))
            self.id = cursor.fetchone()[0]
            return self.id

    @classmethod
    def get_by_game_id(cls, game_id):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                SELECT id, game_id, user_id, category, title, content
                FROM flashcards
                WHERE game_id = %s
                ORDER BY category, created_at
            ''', (game_id,))

            flashcards = []
            for flashcard_data in cursor.fetchall():
                id, game_id, user_id, category, title, content = flashcard_data
                flashcard = cls(game_id, user_id, category, title, content, id)
                flashcards.append(flashcard)

            return flashcards

    @classmethod
    def delete_by_id(cls, flashcard_id):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('DELETE FROM flashcards WHERE id = %s', (flashcard_id,))
            return True