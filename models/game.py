from database import CursorFromConnectionPool
import requests
import xml.etree.ElementTree as Et


class Game:
    """This class represents a board game.
    
    It handles storing game information and fetching data from BoardGameGeek.
    """
    def __init__(self, name, avg_rating, min_players, max_players, image_path, game_id=None, is_expansion=0, yearpublished=None):
        """Create a new Game object.
        
        Args:
            name: The name of the game
            avg_rating: The average user rating (0-10)
            min_players: The minimum number of players
            max_players: The maximum number of players
            image_path: URL to the game's image
            game_id: The game's database ID (None for new games)
            is_expansion: Whether this game is an expansion (0 or 1)
            yearpublished: The year the game was published
        """
        self.id = game_id
        self.name = name
        self.avg_rating = avg_rating
        self.min_players = min_players
        self.max_players = max_players
        self.image_path = image_path
        self.is_expansion = 1 if is_expansion else 0  # Store as 0/1 integer
        self.yearpublished = yearpublished

    def save_to_db(self):
        """Save the game to the database.
        
        If the game has an ID, it will be updated if it exists,
        otherwise a new game will be created.
        
        Returns:
            The game's database ID
        """
        with CursorFromConnectionPool() as cursor:
            if self.id:
                # If ID is provided, check if game already exists
                cursor.execute('SELECT id FROM games WHERE id = %s', (self.id,))
                existing_game = cursor.fetchone()
                
                if existing_game:
                    # Update existing game with new data
                    cursor.execute('''
                        UPDATE games 
                        SET name = %s, avg_rating = %s, min_players = %s, max_players = %s, image_path = %s, 
                            is_expansion = %s, yearpublished = %s
                        WHERE id = %s
                    ''', (self.name, self.avg_rating, self.min_players, self.max_players, self.image_path, 
                          self.is_expansion, self.yearpublished, self.id))
                    return self.id
                else:
                    # Insert new game with provided ID
                    cursor.execute('''
                        INSERT INTO games (id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (self.id, self.name, self.avg_rating, self.min_players, self.max_players, self.image_path, 
                          self.is_expansion, self.yearpublished))
                    return self.id
            else:
                # Standard insert with auto-generated ID
                cursor.execute('''
                    INSERT INTO games (name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                ''', (self.name, self.avg_rating, self.min_players, self.max_players, self.image_path, 
                      self.is_expansion, self.yearpublished))
                self.id = cursor.fetchone()[0]
                return self.id

    @classmethod
    def load_by_id(cls, game_id):
        """Find a game by its database ID.
        
        Args:
            game_id: The database ID to search for
            
        Returns:
            A Game object if found, None otherwise
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished FROM games WHERE id = %s',
                           (game_id,))
            game_data = cursor.fetchone()
            if game_data:
                name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished = game_data
                return cls(name, avg_rating, min_players, max_players, image_path, game_id, is_expansion, yearpublished)
            return None

    @classmethod
    def search_by_name(cls, search_query):
        """Search for games by name in the local database.
        
        Args:
            search_query: The name or ID to search for
            
        Returns:
            A dictionary with three lists: local_games, local_expansions, bgg_games
        """
        games = []
        expansions = []
        
        # Check if search_query is a game ID (numeric)
        is_id_search = search_query.isdigit()
        
        with CursorFromConnectionPool() as cursor:
            if is_id_search:
                # Search by ID (exact match)
                cursor.execute(
                    'SELECT id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished FROM games WHERE id = %s',
                    (search_query,))
            else:
                # Sort results by relevance (exact match first, then startswith, then contains)
                cursor.execute(
                    '''
                    SELECT id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished,
                           CASE 
                               WHEN LOWER(name) = LOWER(%s) THEN 1 
                               WHEN LOWER(name) LIKE LOWER(%s) THEN 2 
                               ELSE 3 
                           END AS match_rank 
                    FROM games 
                    WHERE name ILIKE %s
                    ORDER BY match_rank, avg_rating DESC NULLS LAST, name
                    ''',
                    (search_query, f'{search_query}%', f'%{search_query}%'))
                
            for game_data in cursor.fetchall():
                # Handle ID search (8 columns) vs name search (9 columns with match_rank)
                if is_id_search or len(game_data) == 8:
                    game_id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished = game_data
                else:
                    # Skip the match_rank column for name searches
                    game_id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished, _ = game_data
                
                game = cls(name, avg_rating, min_players, max_players, image_path, game_id, is_expansion, yearpublished)
                game._source = "Local Database"
                
                # Separate games and expansions
                if is_expansion == 1:
                    expansions.append(game)
                else:
                    games.append(game)
        
        # We no longer search BGG API here as it's done separately before this call
        # This prevents duplicate API calls and ensures local DB is updated first
        
        # Return local games and expansions only
        return {"local_games": games, "local_expansions": expansions, "bgg_games": []}

    @classmethod
    def search_bgg_api(cls, name_query):
        """Search for games using the BoardGameGeek API.
        
        Args:
            name_query: The name to search for
            
        Returns:
            A list of Game objects with data from BoardGameGeek
        """
        """Search for games using the BGG XML API2 and update local database"""
        url = f"https://boardgamegeek.com/xmlapi2/search?query={name_query}&type=boardgame"
        try:
            response = requests.get(url)
            
            if response.status_code != 200:
                return []
                
            root = Et.fromstring(response.content)
            games = []
            
            # Get up to 5 games from search results
            for item in root.findall(".//item")[:5]:
                bgg_id = item.get("id")
                game_details = cls.get_bgg_game_details(bgg_id)
                if game_details:
                    # Add source attribute for UI display
                    game_details._source = "BoardGameGeek"
                    games.append(game_details)
                    
            return games
        except Exception as e:
            print(f"Error searching BGG API: {e}")
            return []
        
    @classmethod
    def get_bgg_game_details(cls, bgg_id):
        """Get detailed information about a game from BoardGameGeek.
        
        Args:
            bgg_id: The BoardGameGeek ID of the game
            
        Returns:
            A Game object with data from BoardGameGeek, or None if not found
        """
        """Get detailed game information from BGG API and save to database"""
        url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
        try:
            response = requests.get(url)
            
            if response.status_code != 200:
                return None
                
            root = Et.fromstring(response.content)
            item = root.find(".//item")
            
            if item is None:
                return None
                
            name_element = item.find(".//name[@type='primary']")
            if name_element is None:
                return None
                
            name = name_element.get("value")
            
            # Get rating
            rating_element = item.find(".//statistics/ratings/average")
            avg_rating = float(rating_element.get("value")) if rating_element is not None else 0.0
            # Round to 1 decimal place for display
            avg_rating = round(avg_rating, 1)
            
            # Get player counts
            min_players_element = item.find(".//minplayers")
            min_players = int(min_players_element.get("value")) if min_players_element is not None else 1
            
            max_players_element = item.find(".//maxplayers")
            max_players = int(max_players_element.get("value")) if max_players_element is not None else 1
            
            # Get image
            image_element = item.find(".//image")
            image_path = image_element.text if image_element is not None else ""
            
            # Check if game is an expansion
            is_expansion = 0
            for link in item.findall(".//link"):
                if link.get("type") == "boardgamecategory" and link.get("value") == "Expansion":
                    is_expansion = 1
                    break
                    
            # Get year published
            yearpublished = None
            yearpublished_element = item.find(".//yearpublished")
            if yearpublished_element is not None:
                try:
                    yearpublished = int(yearpublished_element.get("value"))
                except (ValueError, TypeError):
                    pass
                
            # Create game with BGG ID as the game ID
            game = cls(name, avg_rating, min_players, max_players, image_path, game_id=int(bgg_id),
                       is_expansion=is_expansion, yearpublished=yearpublished)
            game.save_to_db()
            
            return game
        except Exception as e:
            print(f"Error getting BGG game details: {e}")
            return None

    def get_flashcards(self):
        """Get all flashcards for this game.
        
        Returns:
            A list of Flashcard objects for this game
        """
        from models.flashcard import Flashcard
        return Flashcard.get_by_game_id(self.id)