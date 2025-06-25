"""Flashcard Model Module.

This module contains the Flashcard class which manages user-created flashcards
for board games. Flashcards contain information that helps users learn about games,
with support for privacy settings and categorization.

The Flashcard class provides functionality for:
- Creating and storing flashcard content
- Privacy management (public vs private flashcards)
- Category-based organization
- User-specific filtering
- Database CRUD operations
"""

from database import CursorFromConnectionPool


class Flashcard:
    """Represents a user-created flashcard for a board game.
    
    Flashcards contain information that helps users learn about games,
    organized by categories and with privacy controls. Each flashcard
    belongs to a specific game and user, with optional privacy settings.
    
    Attributes:
        id (int): Database primary key
        game_id (int): ID of the associated game
        user_id (int): ID of the user who created this flashcard
        category (str): Category for organization (Setup, Rules, Events, etc.)
        title (str): Flashcard title/heading
        content (str): Main flashcard content/text
        is_private (bool): Whether flashcard is private to creator (True) or public (False)
        
    Categories:
        - Setup: Game setup instructions
        - Rules: Game rules and mechanics
        - Events: Special events or situations
        - Points: Scoring information
        - End of the game: End game conditions
        - Notes: General notes and tips
    """
    def __init__(self, game_id, user_id, category, title, content, id=None, is_private=False):
        """Initialize a new Flashcard instance.
        
        Args:
            game_id (int): The ID of the game this flashcard is for
            user_id (int): The ID of the user who created this flashcard
            category (str): The category of the flashcard (Setup, Rules, Events, etc.)
            title (str): The title/heading of the flashcard
            content (str): The main content/text of the flashcard
            id (int, optional): The flashcard's database ID (None for new flashcards)
            is_private (bool, optional): Whether flashcard is private to creator. Defaults to False
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
        
        Inserts a new flashcard record with all current attribute values.
        The flashcard's ID will be set to the new database primary key.
        
        Returns:
            int: The flashcard's database ID
            
        Raises:
            DatabaseError: If database operation fails
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
        
        Used to check for existing flashcards before creating new ones,
        allowing for content appending to existing cards.
        
        Args:
            game_id (int): The ID of the game
            user_id (int): The ID of the user  
            title (str): The exact title of the flashcard
            
        Returns:
            Flashcard: Flashcard object if found, None otherwise
            
        Note:
            This search is case-sensitive and requires exact title match.
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
        """Get all flashcards for a specific game, respecting privacy settings.
        
        Retrieves flashcards associated with a game, filtering based on privacy
        settings and user permissions. Public flashcards are visible to all users,
        while private flashcards are only visible to their creators.
        
        Args:
            game_id (int): The ID of the game to get flashcards for
            current_user_id (int, optional): The ID of the current user.
                If provided, user will see their private flashcards in addition
                to all public flashcards.
                
        Returns:
            list[Flashcard]: List of Flashcard objects for the game, ordered by
                category and creation time
                
        Privacy Rules:
            - If current_user_id is None: Only public flashcards returned
            - If current_user_id provided: Public flashcards + user's private flashcards
            
        Note:
            Results are ordered by category first, then by creation time.
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
        
        Permanently removes the flashcard record from the database.
        This operation cannot be undone.
        
        Args:
            flashcard_id (int): The ID of the flashcard to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            DatabaseError: If database operation fails
            
        Warning:
            This operation is permanent and cannot be undone.
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('DELETE FROM flashcards WHERE id = %s', (flashcard_id,))
            return True
            
    @classmethod
    def load_by_id(cls, flashcard_id):
        """Load a flashcard from the database by its ID.
        
        Args:
            flashcard_id (int): The database ID to search for
            
        Returns:
            Flashcard: Flashcard object if found, None otherwise
            
        Note:
            This loads the complete flashcard with all attributes including
            privacy settings.
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
        """Update the existing flashcard record in the database.
        
        Updates all modifiable fields (category, title, content, is_private)
        for the flashcard with the current ID. The flashcard must already
        exist in the database.
        
        Returns:
            bool: True if update was successful
            
        Raises:
            DatabaseError: If database operation fails
            
        Note:
            The flashcard's ID, game_id, and user_id cannot be changed.
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('''
                UPDATE flashcards 
                SET category = %s, title = %s, content = %s, is_private = %s
                WHERE id = %s
            ''', (self.category, self.title, self.content, self.is_private, self.id))
            return True