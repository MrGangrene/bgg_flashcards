"""Game Model Module.

This module contains the Game class which handles board game data management,
including integration with BoardGameGeek (BGG) API for fetching game information,
image processing, and database operations.

The Game class provides functionality for:
- Searching and storing board game information
- Integration with BoardGameGeek XML API
- Local image storage and management
- Database CRUD operations
- Background data synchronization
"""

from database import CursorFromConnectionPool
import requests
import xml.etree.ElementTree as Et
from utils.image_service import ImageService


class Game:
    """Represents a board game with all its associated data.
    
    This class handles board game information including basic details (name, ratings,
    player counts), images, and integration with the BoardGameGeek (BGG) API.
    
    The class supports both local database storage and remote BGG API fetching,
    with automatic image downloading and local storage for performance.
    
    Attributes:
        id (int): Local database ID (primary key)
        name (str): Game name
        avg_rating (float): Average rating from BGG (0.0-10.0)
        min_players (int): Minimum number of players
        max_players (int): Maximum number of players  
        image_path (str): URL to game image on BGG
        game_id (int): BoardGameGeek ID (same as id for BGG games)
        is_expansion (int): 1 if expansion, 0 if base game
        yearpublished (int): Year the game was published
        
    Private Attributes:
        _source (str): Indicates data source ('Local Database', 'BoardGameGeek', etc.)
        _is_search_data (bool): True if created from BGG search API (basic data only)
    """
    def __init__(self, name, avg_rating, min_players, max_players, image_path, game_id=None, is_expansion=0, yearpublished=None):
        """Initialize a new Game instance.
        
        Args:
            name (str): The name of the game
            avg_rating (float): Average rating from BGG (0.0-10.0)
            min_players (int): Minimum number of players
            max_players (int): Maximum number of players
            image_path (str): URL to the game's image
            game_id (int, optional): BoardGameGeek ID. If None, will be auto-assigned
            is_expansion (int, optional): 1 for expansion, 0 for base game. Defaults to 0
            yearpublished (int, optional): Year the game was published
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
        
        Inserts the game into the games table. If the game already exists
        (based on game_id/BGG ID), it will be updated instead.
        
        Returns:
            int: The database ID of the saved game
            
        Raises:
            DatabaseError: If database operation fails
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
    def search_bgg_api(cls, name_query, cancellation_checker=None, immediate_callback=None):
        """Search for games using the BoardGameGeek API.
        
        Args:
            name_query: The name to search for (or BGG ID as string)
            cancellation_checker: Optional function that returns True if task should be cancelled
            immediate_callback: Optional callback to call with basic results immediately
            
        Returns:
            A list of Game objects with detailed data from BoardGameGeek
        """
        # Check if this is a direct ID search (numeric string)
        if name_query.isdigit():
            # For ID searches, skip the search API and go directly to thing API
            print(f"Direct BGG ID search for game {name_query}")
            try:
                game_details = cls.get_bgg_game_details(name_query)
                if game_details:
                    game_details._source = "BoardGameGeek"
                    
                    # After getting the game by ID, trigger a background search by name
                    # to find and update all variants/editions of this game
                    game_name = game_details.name
                    print(f"Triggering background name search for '{game_name}' after ID lookup")
                    
                    # Use a separate thread to avoid blocking the current response
                    import threading
                    def background_name_search():
                        try:
                            # Small delay to ensure the current ID result is returned first
                            import time
                            time.sleep(1)
                            
                            # Search BGG by name to find all variants/editions
                            print(f"Background: Searching BGG by name '{game_name}'")
                            name_results = cls._search_bgg_by_name(game_name, cancellation_checker)
                            print(f"Background: Found {len(name_results)} additional games by name '{game_name}'")
                        except Exception as err:
                            print(f"Background name search error after ID lookup: {err}")
                    
                    # Start the background name search
                    thread = threading.Thread(target=background_name_search, daemon=True)
                    thread.start()
                    
                    return [game_details]
                else:
                    print(f"No game found for BGG ID {name_query}")
                    return []
            except Exception as e:
                print(f"Error fetching BGG game by ID {name_query}: {e}")
                return []
        
        # For name searches, use the search API
        return cls._search_bgg_by_name(name_query, cancellation_checker, immediate_callback)
    
    @classmethod
    def _search_bgg_by_name(cls, name_query, cancellation_checker=None, immediate_callback=None):
        """Search BGG by name (extracted for reuse in ID searches).
        
        Args:
            name_query: The name to search for
            cancellation_checker: Optional function that returns True if task should be cancelled
            immediate_callback: Optional callback to call with basic results immediately
            
        Returns:
            A list of Game objects with detailed data from BoardGameGeek
        """
        url = f"https://boardgamegeek.com/xmlapi2/search?query={name_query}&type=boardgame"
        try:
            response = requests.get(url)
            
            if response.status_code != 200:
                return []
                
            root = Et.fromstring(response.content)
            search_items = root.findall('.//item')
            
            print(f"BGG search found {len(search_items)} results for '{name_query}'")
            
            # If we have a callback, provide immediate basic results
            if immediate_callback and search_items:
                basic_games = []
                for item in search_items:
                    basic_game = cls._create_basic_game_from_search(item)
                    if basic_game:
                        basic_games.append(basic_game)
                
                if basic_games:
                    print(f"Providing {len(basic_games)} immediate basic results")
                    immediate_callback(basic_games)
            
            # Now get detailed information for each game
            games = []
            for item in search_items:
                # Check for cancellation before processing each game
                if cancellation_checker and cancellation_checker():
                    print(f"⏹️ BGG search cancelled during processing")
                    return games  # Return partial results
                    
                bgg_id = item.get("id")
                print(f"Processing BGG game ID {bgg_id}...")
                game_details = cls.get_bgg_game_details(bgg_id)
                if game_details:
                    # Add source attribute for UI display
                    game_details._source = "BoardGameGeek"
                    games.append(game_details)
            
            print(f"Successfully processed {len(games)} games from BGG")
            return games
        except Exception as e:
            print(f"Error searching BGG API: {e}")
            return []
    
    @classmethod
    def _create_basic_game_from_search(cls, search_item):
        """Create a Game object from BGG search results, prioritizing local database data.
        
        Args:
            search_item: XML element from BGG search results
            
        Returns:
            A Game object with the best available info, or None if invalid
        """
        try:
            bgg_id = search_item.get("id")
            if not bgg_id:
                return None
                
            # First check if we already have this game in the local database
            existing_game = cls.load_by_id(int(bgg_id))
            if existing_game:
                # Use existing database data
                existing_game._source = "Local Database"
                return existing_game
            
            # Game not in database - create from BGG search data
            # Get name - prefer primary name
            name_element = search_item.find(".//name[@type='primary']")
            if name_element is None:
                name_element = search_item.find(".//name")
            if name_element is None:
                return None
                
            name = name_element.get("value")
            
            # Get year published if available
            yearpublished_element = search_item.find(".//yearpublished")
            yearpublished = None
            if yearpublished_element is not None:
                try:
                    yearpublished = int(yearpublished_element.get("value"))
                except (ValueError, TypeError):
                    pass
            
            # Create game object with available search data
            # Don't use placeholder values - use None/0 for missing data
            game = cls(
                name=name,
                avg_rating=0.0,  # Search API doesn't provide rating
                min_players=0,   # Search API doesn't provide player counts
                max_players=0,   # Search API doesn't provide player counts
                image_path="",   # Search API doesn't provide image URL
                game_id=int(bgg_id),
                is_expansion=0,  # Will be determined from detailed data
                yearpublished=yearpublished
            )
            
            # Mark as basic search data (not from database)
            game._source = "BoardGameGeek (Search)"
            game._is_search_data = True
            
            return game
            
        except Exception as e:
            print(f"Error creating game from search result: {e}")
            return None
        
    @classmethod
    def get_bgg_expansions(cls, base_game_id, cancellation_checker=None):
        """Get expansions for a base game from BoardGameGeek.
        
        Args:
            base_game_id: The BGG ID of the base game
            cancellation_checker: Optional function that returns True if task should be cancelled
            
        Returns:
            A list of Game objects representing expansions
        """
        try:
            # First get the base game details to find linked expansions
            url = f"https://boardgamegeek.com/xmlapi2/thing?id={base_game_id}&stats=1"
            response = requests.get(url)
            
            if response.status_code != 200:
                return []
                
            root = Et.fromstring(response.content)
            item = root.find(".//item")
            
            if item is None:
                return []
            
            expansions = []
            
            # Look for expansion links in the BGG data
            for link in item.findall(".//link"):
                if link.get("type") == "boardgameexpansion":
                    # Check for cancellation before processing each expansion
                    if cancellation_checker and cancellation_checker():
                        print(f"⏹️ BGG expansion fetch cancelled during processing")
                        return expansions  # Return partial results
                        
                    expansion_id = link.get("id")
                    
                    # Get detailed information about this expansion
                    expansion_game = cls.get_bgg_game_details(expansion_id)
                    if expansion_game:
                        expansions.append(expansion_game)
            
            return expansions
            
        except Exception as e:
            print(f"Error getting BGG expansions: {e}")
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
                if link.get("type") == "boardgamecategory" and link.get("value") == "Expansion for Base-game":
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
            
            # Immediately download and store image locally if available
            if game.image_path and game.image_path != 'N/A':
                print(f"Downloading image for {game.name}...")
                success = game.download_and_store_image()
                if success:
                    print(f"✅ Image stored for {game.name}")
                else:
                    print(f"❌ Failed to store image for {game.name}")
            
            return game
        except Exception as e:
            print(f"Error getting BGG game details: {e}")
            return None

    def get_flashcards(self, current_user_id=None):
        """Get all flashcards for this game.
        
        Args:
            current_user_id: The ID of the current user (to show their private cards)
        
        Returns:
            A list of Flashcard objects for this game (filtered by privacy)
        """
        from models.flashcard import Flashcard
        return Flashcard.get_by_game_id(self.id, current_user_id)
    
    def get_image_src(self):
        """Get the image source for display in UI.
        
        Returns dict with either 'src' or 'src_base64' for Flet Image component.
        
        Returns:
            Dict containing either 'src' (URL) or 'src_base64' (base64 data)
        """
        if self.id:
            # Try to get local image first
            base64_image = ImageService.get_image_as_base64(self.id)
            if base64_image:
                # Extract just the base64 part (remove data:image/jpeg;base64, prefix)
                if base64_image.startswith('data:'):
                    base64_data = base64_image.split(',', 1)[1]
                    return {'src_base64': base64_data}
        
        # If we have an external URL, use it
        if self.image_path and self.image_path != 'N/A' and self.image_path.strip():
            return {'src': self.image_path}
        
        # Fall back to local placeholder image (stored with ID -1)
        placeholder_image = ImageService.get_image_as_base64(-1)
        if placeholder_image and placeholder_image.startswith('data:'):
            base64_data = placeholder_image.split(',', 1)[1]
            return {'src_base64': base64_data}
        
        # Final fallback to remote URL if local placeholder fails
        return {'src': 'https://cf.geekdo-images.com/zxVVmggfpHJpmnJY9j-k1w__imagepage/img/6AJ0hDAeJlICZkzaeIhZA_fSiAI=/fit-in/900x600/filters:no_upscale():strip_icc()/pic1657689.jpg'}
    
    def download_and_store_image(self, force_update=False):
        """Download and store the image locally in the database.
        
        Args:
            force_update: If True, download even if image already exists
        
        Returns:
            True if successful, False otherwise
        """
        if not self.id or not self.image_path or self.image_path == 'N/A':
            return False
        
        # Skip if image already exists (unless forcing update)
        if not force_update and self._has_local_image():
            print(f"Image already exists for {self.name}, skipping download")
            return True
        
        return ImageService.download_and_store_image(self.id, self.image_path)

    def _has_local_image(self):
        """Check if this game already has a locally stored image.
        
        Returns:
            True if local image exists, False otherwise
        """
        with CursorFromConnectionPool() as cursor:
            cursor.execute(
                'SELECT image_oid FROM games WHERE id = %s AND image_oid IS NOT NULL',
                (self.id,)
            )
            return cursor.fetchone() is not None