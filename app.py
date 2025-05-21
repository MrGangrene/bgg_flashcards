import flet as ft
from typing import Optional

from client.api_client import ApiClient
from models.user import User
from pages.auth_page import AuthPage
from pages.main_page import MainPage
from pages.game_search_page import GameSearchPage
from pages.game_detail_page import GameDetailPage
from pages.create_flashcard_page import CreateFlashcardPage


def main(page: ft.Page):
    """This is the main function that runs our app.
    
    It sets up the API client, handles routing between pages,
    and manages user login state.
    
    Args:
        page: The main Flet page that will hold our app
    """
    page.title = "Board Game Flashcards"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0

    # Application state
    current_user: Optional[User] = None
    api_client = ApiClient("http://localhost:8000")  # Default to localhost API

    def add_view(route_path, controls, vertical_alignment=None, horizontal_alignment=None):
        """Helper function to add a view to the page.
        
        Args:
            route_path: The route for the view
            controls: List of controls to display
            vertical_alignment: Optional vertical alignment
            horizontal_alignment: Optional horizontal alignment
        """
        view_props = {
            "route": route_path,
            "controls": controls
        }
        
        if vertical_alignment:
            view_props["vertical_alignment"] = vertical_alignment
        
        if horizontal_alignment:
            view_props["horizontal_alignment"] = horizontal_alignment
            
        page.views.append(ft.View(**view_props))

    # Function to handle route changes
    def route_change(route):
        """This function updates the page when the user navigates to a new route.
        
        It clears the current view and loads the appropriate page based on the URL.
        It also checks if the user is logged in before showing protected pages.
        
        Args:
            route: Contains information about the requested URL
        """
        if not current_user and route.route != "/login":
            # Redirect to log in if not authenticated
            page.go("/login")
            return

        page.views.clear()
            
        if route.route == "/login":
            add_view(
                "/login", 
                [auth_page.build()], 
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        elif route.route == "/":
            # Main page with user's saved games
            main_page = MainPage(
                page=page,
                user=current_user,
                on_game_select=lambda selected_game_id: page.go(f"/game/{selected_game_id}"),
                on_add_game=lambda: page.go("/search"),
                on_logout=logout
            )
            add_view("/", [main_page.build()])
        elif route.route == "/search":
            # Game search page
            search_page = GameSearchPage(
                page=page,
                user=current_user,
                on_save_game=lambda: page.go("/"),
                on_back=lambda: page.go("/")
            )
            add_view("/search", [search_page.build()])
        elif route.route.startswith("/game/") and "/create_flashcard/" in route.route:
            # Create flashcard page with category
            # Extract the game_id and category from the route
            path_parts = route.route.split("/")
            game_id = int(path_parts[-3])  # Game ID is now third-to-last
            category = path_parts[-1]  # Category is now the last part
            
            # Type assertion for PyCharm
            assert current_user is not None, "User must be logged in"
            
            create_page = CreateFlashcardPage(
                page=page,
                game_id=game_id,
                user_id=current_user.id,
                default_category=category,
                on_save=lambda: page.go(f"/game/{game_id}"),
                on_back=lambda: page.go(f"/game/{game_id}")
            )
            add_view(f"/game/{game_id}/create_flashcard/{category}", [create_page.build()])
        elif route.route.startswith("/game/") and route.route.endswith("/edit_flashcard"):
            # Edit flashcard page - now using CreateFlashcardPage in edit mode
            # Extract the flashcard_id from the route
            parts = route.route.split("/")
            flashcard_id = int(parts[-2])
            game_id = int(parts[-4])  # Game ID is needed for navigation
            
            edit_page = CreateFlashcardPage(
                page=page,
                flashcard_id=flashcard_id,
                on_save=lambda: page.go(f"/game/{game_id}"),
                on_back=lambda: page.go(f"/game/{game_id}")
            )
            add_view(f"/game/{game_id}/flashcard/{flashcard_id}/edit_flashcard", [edit_page.build()])
        elif route.route.startswith("/game/") and not route.route.endswith("/create_flashcard") and not route.route.endswith("/edit_flashcard"):
            # Game detail page with flashcards
            game_id = int(route.route.split("/")[-1])
            # Type assertion for PyCharm
            assert current_user is not None, "User must be logged in"
            
            game_page = GameDetailPage(
                page=page,
                game_id=game_id,
                user_id=current_user.id,
                on_create_flashcard=lambda selected_game_id, selected_category: page.go(f"/game/{selected_game_id}/create_flashcard/{selected_category}"),
                on_edit_flashcard=lambda selected_flashcard_id: page.go(f"/game/{game_id}/flashcard/{selected_flashcard_id}/edit_flashcard"),
                on_back=lambda: page.go("/")
            )
            add_view(f"/game/{game_id}", [game_page.build()])

        page.update()

    def logout():
        """Log out the current user and return to the login page.
        
        This clears the current_user variable and redirects to the login page.
        """
        nonlocal current_user
        current_user = None
        page.go("/login")

    def on_login(user):
        """Handle successful user login.
        
        This sets the current_user and redirects to the main page.
        
        Args:
            user: The User object that successfully logged in
        """
        nonlocal current_user
        current_user = user
        page.go("/")

    auth_page = AuthPage(page, on_login, api_client)

    page.on_route_change = route_change
    page.go("/login")


ft.app(target=main)