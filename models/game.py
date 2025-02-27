from database import CursorFromConnectionPool
import requests
import xml.etree.ElementTree as Et


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
        # First search local database
        with CursorFromConnectionPool() as cursor:
            cursor.execute(
                'SELECT id, name, avg_rating, min_players, max_players, image_path FROM games WHERE name ILIKE %s',
                (f'%{name_query}%',))
            games = []
            for game_data in cursor.fetchall():
                game_id, name, avg_rating, min_players, max_players, image_path = game_data
                games.append(cls(name, avg_rating, min_players, max_players, image_path, game_id))
            
            # If no results from database, search BGG API
            if not games:
                bgg_games = cls.search_bgg_api(name_query)
                games.extend(bgg_games)
                
            return games

    @classmethod
    def search_bgg_api(cls, name_query):
        """Search for games using the BGG XML API2"""
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
            
            # Create and save game to database
            game = cls(name, avg_rating, min_players, max_players, image_path)
            game.save_to_db()
            
            return game
        except Exception as e:
            print(f"Error getting BGG game details: {e}")
            return None

    def get_flashcards(self):
        from models.flashcard import Flashcard
        return Flashcard.get_by_game_id(self.id)