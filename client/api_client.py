import requests
import json
from typing import Dict, List, Optional, Any, Union


class ApiClient:
    """API client for interacting with the BGG Flashcards API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client.
        
        Args:
            base_url: The base URL of the API
        """
        self.base_url = base_url
        self.token = None
    
    def login(self, username: str, password: str) -> bool:
        """Log in to the API.
        
        Args:
            username: The username for authentication
            password: The password for authentication
            
        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/token",
                data={"username": username, "password": password},
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                return True
            return False
        except requests.RequestException:
            return False
    
    def register(self, username: str, email: str, password: str) -> Dict:
        """Register a new user.
        
        Args:
            username: The username for registration
            email: The email for registration
            password: The password for registration
            
        Returns:
            Dict: Response from the API
        """
        try:
            response = requests.post(
                f"{self.base_url}/users/",
                json={"username": username, "email": email, "password": password}
            )
            return response.json() if response.status_code == 200 else {"error": response.text}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def _get_headers(self) -> Dict:
        """Get headers for authenticated requests.
        
        Returns:
            Dict: Headers including authentication token if available
        """
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def get_user_info(self) -> Dict:
        """Get information about the current user.
        
        Returns:
            Dict: User information or error
        """
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self._get_headers()
            )
            return response.json() if response.status_code == 200 else {"error": response.text}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def search_games(self, query: str) -> Dict:
        """Search for games by name.
        
        Args:
            query: The search query
            
        Returns:
            Dict: Search results or error
        """
        try:
            response = requests.post(
                f"{self.base_url}/games/search",
                headers=self._get_headers(),
                json={"query": query}
            )
            return response.json() if response.status_code == 200 else {"error": response.text}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def search_bgg(self, query: str) -> List:
        """Search for games on BoardGameGeek.
        
        Args:
            query: The search query
            
        Returns:
            List: BGG search results or error
        """
        try:
            response = requests.post(
                f"{self.base_url}/games/search_bgg",
                headers=self._get_headers(),
                json={"query": query}
            )
            return response.json() if response.status_code == 200 else []
        except requests.RequestException as e:
            return []
    
    def get_game(self, game_id: int) -> Dict:
        """Get a game by ID.
        
        Args:
            game_id: The ID of the game
            
        Returns:
            Dict: Game details or error
        """
        try:
            response = requests.get(
                f"{self.base_url}/games/{game_id}",
                headers=self._get_headers()
            )
            return response.json() if response.status_code == 200 else {"error": response.text}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_user_games(self) -> List:
        """Get games saved by the current user.
        
        Returns:
            List: User's saved games or empty list on error
        """
        try:
            response = requests.get(
                f"{self.base_url}/users/me/games",
                headers=self._get_headers()
            )
            return response.json() if response.status_code == 200 else []
        except requests.RequestException as e:
            return []
    
    def save_game(self, game_id: int) -> bool:
        """Save a game to the user's collection.
        
        Args:
            game_id: The ID of the game to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/users/me/games",
                headers=self._get_headers(),
                json={"game_id": game_id}
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def remove_game(self, game_id: int) -> bool:
        """Remove a game from the user's collection.
        
        Args:
            game_id: The ID of the game to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.delete(
                f"{self.base_url}/users/me/games/{game_id}",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_game_flashcards(self, game_id: int) -> List:
        """Get flashcards for a game.
        
        Args:
            game_id: The ID of the game
            
        Returns:
            List: Flashcards for the game or empty list on error
        """
        try:
            response = requests.get(
                f"{self.base_url}/games/{game_id}/flashcards",
                headers=self._get_headers()
            )
            return response.json() if response.status_code == 200 else []
        except requests.RequestException:
            return []
    
    def create_flashcard(self, game_id: int, category: str, title: str, content: str) -> Dict:
        """Create a new flashcard.
        
        Args:
            game_id: The ID of the game
            category: The category of the flashcard
            title: The title of the flashcard
            content: The content of the flashcard
            
        Returns:
            Dict: Created flashcard details or error
        """
        try:
            response = requests.post(
                f"{self.base_url}/flashcards",
                headers=self._get_headers(),
                json={
                    "game_id": game_id,
                    "category": category,
                    "title": title,
                    "content": content
                }
            )
            return response.json() if response.status_code == 200 else {"error": response.text}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_flashcard(self, flashcard_id: int) -> Dict:
        """Get a flashcard by ID.
        
        Args:
            flashcard_id: The ID of the flashcard
            
        Returns:
            Dict: Flashcard details or error
        """
        try:
            response = requests.get(
                f"{self.base_url}/flashcards/{flashcard_id}",
                headers=self._get_headers()
            )
            return response.json() if response.status_code == 200 else {"error": response.text}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def update_flashcard(self, flashcard_id: int, game_id: int, category: str, title: str, content: str) -> Dict:
        """Update a flashcard.
        
        Args:
            flashcard_id: The ID of the flashcard to update
            game_id: The ID of the game
            category: The category of the flashcard
            title: The title of the flashcard
            content: The content of the flashcard
            
        Returns:
            Dict: Updated flashcard details or error
        """
        try:
            response = requests.put(
                f"{self.base_url}/flashcards/{flashcard_id}",
                headers=self._get_headers(),
                json={
                    "game_id": game_id,
                    "category": category,
                    "title": title,
                    "content": content
                }
            )
            return response.json() if response.status_code == 200 else {"error": response.text}
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def delete_flashcard(self, flashcard_id: int) -> bool:
        """Delete a flashcard.
        
        Args:
            flashcard_id: The ID of the flashcard to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.delete(
                f"{self.base_url}/flashcards/{flashcard_id}",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except requests.RequestException:
            return False