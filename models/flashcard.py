from database import CursorFromConnectionPool


class Flashcard:
    """This class represents a flashcard for a board game.
    
    Flashcards contain information that helps users learn about games.
    """
    def __init__(self, game_id, user_id, category, title, content, id=None, is_private=False):
        """Create a new Flashcard object.
        
        Args:
            game_id: The ID of the game this flashcard is for
            user_id: The ID of the user who created this flashcard
            category: The category of the flashcard (e.g., 'Rules', 'Strategy')
            title: The title of the flashcard
            content: The content/text of the flashcard
            id: The flashcard's database ID (None for new flashcards)
        """
        self.id = id
        self.game_id = game_id
        self.user_id = user_id
        self.category = category
        self.title = title
        self.content = content
        self.is_private = is_private

    def save_to_db(self):
        """Save the flashcard to the database.
        
        Returns:
            The flashcard's database ID
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                INSERT INTO flashcards (game_id, user_id, category, title, content, is_private) 
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            ''', (self.game_id, self.user_id, self.category, self.title, self.content, self.is_private))
            self.id = cursor.fetchone()[0]
            return self.id
    
    @classmethod
    def find_by_game_user_title(cls, game_id, user_id, title):
        """Find a flashcard by game ID, user ID, and title.
        
        Args:
            game_id: The ID of the game
            user_id: The ID of the user
            title: The title of the flashcard
            
        Returns:
            A Flashcard object if found, None otherwise
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                SELECT id, game_id, user_id, category, title, content, is_private
                FROM flashcards
                WHERE game_id = %s AND user_id = %s AND title = %s
            ''', (game_id, user_id, title))
            
            flashcard_data = cursor.fetchone()
            if flashcard_data:
                id, game_id, user_id, category, title, content, is_private = flashcard_data
                return cls(game_id, user_id, category, title, content, id, is_private)
            return None

    @classmethod
    def get_by_game_id(cls, game_id, current_user_id=None):
        """Get all flashcards for a specific game.
        
        Args:
            game_id: The ID of the game to get flashcards for
            current_user_id: The ID of the current user (to show their private cards)
            
        Returns:
            A list of Flashcard objects for the game (filtered by privacy)
        """
        with CursorFromConnectionPool() as cursor:
            if current_user_id:
                # Show public cards + private cards belonging to the current user
                cursor.execute('''
                    SELECT id, game_id, user_id, category, title, content, is_private
                    FROM flashcards
                    WHERE game_id = %s AND (is_private = FALSE OR user_id = %s)
                    ORDER BY category, created_at
                ''', (game_id, current_user_id))
            else:
                # Show only public cards
                cursor.execute('''
                    SELECT id, game_id, user_id, category, title, content, is_private
                    FROM flashcards
                    WHERE game_id = %s AND is_private = FALSE
                    ORDER BY category, created_at
                ''', (game_id,))

            flashcards = []
            for flashcard_data in cursor.fetchall():
                id, game_id, user_id, category, title, content, is_private = flashcard_data
                flashcard = cls(game_id, user_id, category, title, content, id, is_private)
                flashcards.append(flashcard)

            return flashcards

    @classmethod
    def delete_by_id(cls, flashcard_id):
        """Delete a flashcard from the database.
        
        Args:
            flashcard_id: The ID of the flashcard to delete
            
        Returns:
            True if successful
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('DELETE FROM flashcards WHERE id = %s', (flashcard_id,))
            return True
            
    @classmethod
    def load_by_id(cls, flashcard_id):
        """Find a flashcard by its database ID.
        
        Args:
            flashcard_id: The database ID to search for
            
        Returns:
            A Flashcard object if found, None otherwise
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT game_id, user_id, category, title, content, is_private FROM flashcards WHERE id = %s', 
                           (flashcard_id,))
            flashcard_data = cursor.fetchone()
            if flashcard_data:
                game_id, user_id, category, title, content, is_private = flashcard_data
                return cls(game_id, user_id, category, title, content, flashcard_id, is_private)
            return None
            
    def update(self):
        """Update the flashcard in the database.
        
        Returns:
            True if successful
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                UPDATE flashcards 
                SET category = %s, title = %s, content = %s, is_private = %s
                WHERE id = %s
            ''', (self.category, self.title, self.content, self.is_private, self.id))
            return True