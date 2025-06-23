"""
BGG Database Synchronization Script

This script syncs the local database with BoardGameGeek data by:
1. Searching for games by name on BoardGameGeek
2. Bulk updating all matching games in one operation
3. Rate-limiting API calls to avoid being blocked

Usage:
    python update_db_with_bgg.py --query <search_term> [--images]

Parameters:
    --query:      Search term to look up games (e.g. "Catan", "Pandemic", "a")
    --letter:     Single letter to search for all games starting with that letter
    --limit:      Maximum number of games to process (default: 50)
    --images:     Only process games with missing images in the local database
"""

import argparse
import time
import xml.etree.ElementTree as Et
import requests
from database import CursorFromConnectionPool, Database
from models.game import Game
from config import DB_CONFIG


def parse_arguments():
    """Parse command line arguments for the script.
    
    Returns:
        An argparse.Namespace object containing the arguments
    """
    parser = argparse.ArgumentParser(description='Update local database with BoardGameGeek data')
    
    search_group = parser.add_mutually_exclusive_group()
    search_group.add_argument('--query', type=str, help='Search term to look up games (e.g. "Catan", "Pandemic")')
    search_group.add_argument('--letter', type=str, help='Single letter to search for all games starting with that letter')
    
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of games to process')
    parser.add_argument('--images', action='store_true', help='Only process games with missing images')
    return parser.parse_args()


def get_game_from_bgg(bgg_id):
    """Fetch game details from BGG API and update local database"""
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    try:
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Error: BGG API returned status code {response.status_code} for ID {bgg_id}")
            return None

        root = Et.fromstring(response.content)
        item = root.find(".//item")
        
        if item is None:
            print(f"Warning: No data found for game ID {bgg_id}")
            return None
            
        name_element = item.find(".//name[@type='primary']")
        if name_element is None:
            print(f"Warning: No name found for game ID {bgg_id}")
            return None
            
        name = name_element.get("value")
        
        # Get rating
        rating_element = item.find(".//statistics/ratings/average")
        avg_rating = float(rating_element.get("value")) if rating_element is not None else 0.0
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
        game = Game(name, avg_rating, min_players, max_players, image_path, id=int(bgg_id), 
                    is_expansion=is_expansion, yearpublished=yearpublished)
        
        # Save to database
        game.save_to_db()
        return game
    
    except Exception as e:
        print(f"Error processing game ID {bgg_id}: {e}")
        return None


def check_if_game_exists(bgg_id):
    """Check if a game with the given BGG ID exists in the database.
    
    Args:
        bgg_id: The BoardGameGeek ID to check
        
    Returns:
        True if the game exists, False otherwise
    """
    with CursorFromConnectionPool() as cursor:
        cursor.execute('SELECT id FROM games WHERE id = %s', (bgg_id,))
        return cursor.fetchone() is not None


def get_games_with_missing_images(limit=1000, distinct_names=False):
    """
    Get games with missing images in the database
    
    Args:
        limit: Maximum number of games to return
        distinct_names: If True, return only one game per distinct game name
    
    Returns:
        List of tuples containing (id, name) for games with missing images
    """
    with CursorFromConnectionPool() as cursor:
        # Count how many games need image updates
        cursor.execute("SELECT COUNT(*) FROM games WHERE image_path IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"Found {null_count} games with missing images in database")
        
        if distinct_names:
            # Get only one representative game per unique game name
            cursor.execute('''
                WITH RankedGames AS (
                    SELECT 
                        id, 
                        name,
                        ROW_NUMBER() OVER (PARTITION BY LOWER(name) ORDER BY id) as rn
                    FROM games 
                    WHERE image_path IS NULL
                )
                SELECT id, name FROM RankedGames 
                WHERE rn = 1
                ORDER BY name
                LIMIT %s
            ''', (limit,))
        else:
            # Get all games with missing images - simpler query focused on NULL values
            cursor.execute('''
                SELECT id, name FROM games 
                WHERE image_path IS NULL
                ORDER BY id
                LIMIT %s
            ''', (limit,))
            
        results = [(row[0], row[1]) for row in cursor.fetchall()]
        return results


def search_bgg_by_query(query, limit=100):
    """Search for games on BGG by name and update the local database.
    
    Args:
        query: The search query to find games
        limit: Maximum number of games to return
        
    Returns:
        List of BGG game IDs matching the search
    """
    print(f"Searching for games matching: '{query}'")
    url = f"https://boardgamegeek.com/xmlapi2/search?query={query}&type=boardgame"
    
    try:
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Error: BGG API returned status code {response.status_code}")
            return []
            
        root = Et.fromstring(response.content)
        items = root.findall(".//item")
        
        total_found = len(items)
        processing_limit = min(limit, total_found)
        
        print(f"Found {total_found} games on BGG matching '{query}'")
        print(f"Will process up to {processing_limit} games")
        
        game_ids = []
        for item in items[:processing_limit]:
            bgg_id = item.get("id")
            game_ids.append(bgg_id)
            
        return game_ids
    
    except Exception as e:
        print(f"Error searching BGG API: {e}")
        return []


def search_bgg_by_letter(letter, limit=100):
    """Search for games on BGG starting with a specific letter.
    
    Args:
        letter: The single letter to search for games starting with
        limit: Maximum number of games to return
        
    Returns:
        List of BGG game IDs matching the search
    """
    if len(letter) != 1:
        print("Error: --letter argument must be a single character")
        return []
        
    print(f"Searching for games starting with letter: '{letter}'")
    # Exact match at the beginning of the name 
    url = f"https://boardgamegeek.com/xmlapi2/search?query={letter}&type=boardgame&exact=1"
    
    try:
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Error: BGG API returned status code {response.status_code}")
            return []
            
        root = Et.fromstring(response.content)
        items = root.findall(".//item")
        
        total_found = len(items)
        processing_limit = min(limit, total_found)
        
        print(f"Found {total_found} games on BGG starting with '{letter}'")
        print(f"Will process up to {processing_limit} games")
        
        game_ids = []
        for item in items[:processing_limit]:
            bgg_id = item.get("id")
            game_ids.append(bgg_id)
            
        return game_ids
    
    except Exception as e:
        print(f"Error searching BGG API: {e}")
        return []


def update_games_with_missing_images(limit=50):
    """Update games with missing images, using one distinct game name at a time"""
    print("Starting database update for games with missing images")
    
    # Get games with missing images, one per distinct name
    games_to_update = get_games_with_missing_images(limit=limit, distinct_names=True)
    
    if not games_to_update:
        print("No games with missing images found in the database.")
        return
        
    total_games = len(games_to_update)
    print(f"Found {total_games} distinct game names with missing images")
    print(f"Will search BGG for each game name, one at a time")
    print("Press Ctrl+C to stop at any time\n")
    
    processed = 0
    successful = 0
    skipped = 0
    
    try:
        for game_id, game_name in games_to_update:
            print(f"Processing: {game_name} (ID: {game_id})")
            
            start_time = time.time()
            
            # Search BGG using the game's name instead of ID
            print(f"Searching BGG for: {game_name}")
            bgg_results = search_bgg_by_query(game_name, limit=5)
            
            if not bgg_results:
                print(f"❌ No matches found on BGG for '{game_name}'")
                skipped += 1
            else:
                # Try to find an exact match or close match
                bgg_id = bgg_results[0]  # Use the first result by default
                
                # Get the game details from BGG and update local DB
                print(f"Getting details for BGG ID: {bgg_id}")
                game = get_game_from_bgg(bgg_id)
                
                if game:
                    if game.image_path and game.image_path.strip():
                        # Game has a valid image path
                        print(f"✅ Successfully updated: {game.name}")
                        print(f"   New image URL: {game.image_path}")
                        
                        # Find all records with the same name and update them too
                        with CursorFromConnectionPool() as cursor:
                            cursor.execute('''
                                UPDATE games
                                SET image_path = %s
                                WHERE LOWER(name) = LOWER(%s)
                                   AND image_path IS NULL
                            ''', (game.image_path, game_name))
                            
                            rows_updated = cursor.rowcount
                            
                        print(f"   Updated {rows_updated} games with name '{game_name}'")
                        successful += 1
                    else:
                        # Game exists but has no image - mark as N/A so we don't process it again
                        print(f"⚠️ Game found but has no image: '{game.name}'")
                        print(f"   Marking as 'N/A' in database")
                        
                        with CursorFromConnectionPool() as cursor:
                            cursor.execute('''
                                UPDATE games
                                SET image_path = 'N/A'
                                WHERE LOWER(name) = LOWER(%s)
                                   AND image_path IS NULL
                            ''', (game_name,))
                            
                            rows_updated = cursor.rowcount
                            
                        print(f"   Marked {rows_updated} games with name '{game_name}' as 'N/A'")
                        # Count this as successful since we've handled it
                        successful += 1
                else:
                    print(f"❌ Failed to get game data for '{game_name}'")
                    skipped += 1
            
            processed += 1
            
            # Calculate time to sleep between API requests
            elapsed = time.time() - start_time
            sleep_time = 3  # Fixed sleep time to avoid rate limiting
            
            # Progress report
            if processed % 5 == 0 or processed == total_games:
                print(f"\nProgress Report:")
                print(f"  Processed: {processed}/{total_games} distinct game names")
                print(f"  Successful updates: {successful}")
                print(f"  Failed updates: {skipped}")
                print(f"  Approximate time remaining: {((total_games - processed) * 15) // 60} minutes\n")
            
            if processed < total_games:
                print(f"Waiting {sleep_time:.1f} seconds before next request...")
                time.sleep(sleep_time)  # time.sleep accepts float values
                
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        print(f"Progress: {processed}/{total_games} games processed")
    
    print("\nDatabase update completed!")
    print(f"  Total distinct game names processed: {processed}")
    print(f"  Successfully updated: {successful}")
    print(f"  Failed: {skipped}")


def update_database(search_query=None, search_letter=None, limit=50, images_only=False):
    """Update local database with data from BoardGameGeek.
    
    Args:
        search_query: The search term to look for games (e.g. "Catan")
        search_letter: Single letter to search for all games starting with that letter
        limit: Maximum number of games to process
        images_only: If True, only process games with missing images
    """
    
    # Special handling for image-only mode
    if images_only:
        return update_games_with_missing_images(limit)
        
    print("Starting database update from BoardGameGeek")
    print(f"Processing limit: {limit} games")
    
    if search_query:
        games_to_update = search_bgg_by_query(search_query, limit)
        
        if not games_to_update:
            print(f"No games found matching '{search_query}'")
            return
            
    elif search_letter:
        games_to_update = search_bgg_by_letter(search_letter, limit)
        
        if not games_to_update:
            print(f"No games found starting with '{search_letter}'")
            return
    else:
        print("Error: Must specify either --query or --letter")
        return
    
    print("Press Ctrl+C to stop at any time\n")
    
    processed = 0
    successful = 0
    skipped = 0
    
    try:
        for game_id in games_to_update:
            print(f"Processing game ID {game_id}...")
                
            start_time = time.time()
            game = get_game_from_bgg(game_id)
            
            if game:
                # Successfully got the game from BGG
                if not game.image_path or not game.image_path.strip():
                    # Game has no image - update it to mark as N/A
                    with CursorFromConnectionPool() as cursor:
                        cursor.execute('UPDATE games SET image_path = %s WHERE id = %s', ('N/A', game.id))
                    print(f"⚠️ Successfully processed: {game.name} (ID: {game.id}, Year: {game.yearpublished})")
                    print(f"   Note: No image available, marked as 'N/A'")
                else:
                    print(f"✅ Successfully processed: {game.name} (ID: {game.id}, Year: {game.yearpublished})")
                    print(f"   Image URL: {game.image_path}")
                successful += 1
            else:
                print(f"❌ Failed to process game ID {game_id}")
                skipped += 1
                
            processed += 1
            
            # Calculate time to sleep to maintain 15-second interval
            elapsed = time.time() - start_time
            sleep_time = max(0, 15 - elapsed)
            
            # Progress report
            if processed % 5 == 0 or processed == len(games_to_update):
                print(f"\nProgress Report:")
                print(f"  Processed: {processed}/{len(games_to_update)} games")
                print(f"  Successful: {successful}")
                print(f"  Skipped: {skipped}")
                print(f"  Approximate time remaining: {((len(games_to_update) - processed) * 15) // 60} minutes\n")
            
            if processed < len(games_to_update):
                print(f"Waiting {sleep_time:.1f} seconds before next request...")
                time.sleep(sleep_time)  # time.sleep accepts float values
                
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        print(f"Progress: {processed}/{len(games_to_update)} games processed")
    
    print("\nDatabase update completed!")
    print(f"  Total processed: {processed}")
    print(f"  Successfully added/updated: {successful}")
    print(f"  Skipped: {skipped}")


def initialize_database():
    """Initialize the database connection.
    
    This sets up the connection pool with the database parameters.
    """
    # Initialize the database using the configuration from config.py
    Database.initialize(**DB_CONFIG)


if __name__ == "__main__":
    args = parse_arguments()
    
    # Initialize the database connection before using it
    initialize_database()
    
    # Now run the update process with the new search-based approach
    update_database(
        search_query=args.query, 
        search_letter=args.letter,
        limit=args.limit, 
        images_only=args.images
    )