import flet as ft
from database import Database, DatabaseError
from pages.auth_page import AuthPage
from pages.main_page import MainPage
from pages.game_search_page import GameSearchPage
from pages.game_detail_page import GameDetailPage
from pages.create_flashcard_page import CreateFlashcardPage
from pages.db_error_page import DbErrorPage


def main(page: ft.Page):
    """This is the main function that runs our app.
    
    It sets up the database, handles routing between pages,
    and manages user login state.
    
    Args:
        page: The main Flet page that will hold our app
    """
    page.title = "Board Game Flashcards"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0

    # Application state
    current_user = None
    db_connected = False
    
    # Function to initialize database connection
    def initialize_database():
        nonlocal db_connected
        try:
            # Initialize database connection
            Database.initialize(
                minconn=1,
                maxconn=10,
                database="bgg_flashcards",
                # user="stephen.van.cauwenberghe",
                # password="password",
                user="stephenvc",
                password="UsCAxzFPGT217HHjXvEQCAThUU8ciZ5Z8gAH9FxxKI3e5qzBQn",
                host="10.0.0.150",
                # host="localhost",
                port="5432"
            )
            db_connected = True
            # If we were showing the error page, redirect to log in
            if page.route == "/db_error":
                page.go("/login")
            return True
        except DatabaseError:
            db_connected = False
            # Show database error page
            show_db_error_page()
            return False
    
    # Initialize database on startup
    initialize_database()
    
    # Function to show database error page
    def show_db_error_page():
        """Show the database error page and clear other views."""
        page.views.clear()
        db_error_page = DbErrorPage(
            page=page,
            on_retry=initialize_database
        )
        page.views.append(
            ft.View(
                route="/db_error",
                controls=[db_error_page.build()],
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()

    # Function to handle route changes
    def route_change(route):
        """This function updates the page when the user navigates to a new route.
        
        It clears the current view and loads the appropriate page based on the URL.
        It also checks if the user is logged in before showing protected pages.
        
        Args:
            route: Contains information about the requested URL
        """
        # If database is not connected, and we're not already on the error page,
        # redirect to the database error page
        if not db_connected and route.route != "/db_error":
            show_db_error_page()
            return
            
        page.views.clear()

        if route.route == "/db_error":
            show_db_error_page()
            return
            
        if not current_user and route.route != "/login":
            # Redirect to log in if not authenticated
            page.go("/login")
            return

        if route.route == "/login":
            page.views.append(
                ft.View(
                    route="/login",
                    controls=[auth_page.build()],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        elif route.route == "/":
            # Main page with user's saved games
            main_page = MainPage(
                page=page,
                user=current_user,
                on_game_select=lambda game_id: page.go(f"/game/{game_id}"),
                on_add_game=lambda: page.go("/search"),
                on_logout=logout
            )
            page.views.append(
                ft.View(
                    route="/",
                    controls=[main_page.build()],
                )
            )
        elif route.route == "/search":
            # Game search page
            search_page = GameSearchPage(
                page=page,
                user=current_user,
                on_save_game=lambda: page.go("/"),
                on_back=lambda: page.go("/")
            )
            page.views.append(
                ft.View(
                    route="/search",
                    controls=[search_page.build()],
                )
            )

        elif route.route.startswith("/game/") and "/create_flashcard/" in route.route:
            # Create flashcard page with category
            # Extract the game_id and category from the route
            path_parts = route.route.split("/")
            game_id = int(path_parts[-3])  # Game ID is now third-to-last
            category = path_parts[-1]  # Category is now the last part
            
            create_page = CreateFlashcardPage(
                page=page,
                game_id=game_id,
                user_id=current_user.id,
                default_category=category,
                on_save=lambda: page.go(f"/game/{game_id}"),
                on_back=lambda: page.go(f"/game/{game_id}")
            )
            page.views.append(
                ft.View(
                    route=f"/game/{game_id}/create_flashcard/{category}",
                    controls=[create_page.build()],
                )
            )

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
            page.views.append(
                ft.View(
                    route=f"/game/{game_id}/flashcard/{flashcard_id}/edit_flashcard",
                    controls=[edit_page.build()],
                )
            )
        elif route.route.startswith("/game/") and not route.route.endswith("/create_flashcard") and not route.route.endswith("/edit_flashcard"):
            # Game detail page with flashcards
            game_id = int(route.route.split("/")[-1])
            game_page = GameDetailPage(
                page=page,
                game_id=game_id,
                user_id=current_user.id,
                on_create_flashcard=lambda game_id, category: page.go(f"/game/{game_id}/create_flashcard/{category}"),
                on_edit_flashcard=lambda flashcard_id: page.go(f"/game/{game_id}/flashcard/{flashcard_id}/edit_flashcard"),
                on_back=lambda: page.go("/")
            )
            page.views.append(
                ft.View(
                    route=f"/game/{game_id}",
                    controls=[game_page.build()],
                )
            )

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
        It checks if database is connected before proceeding.
        
        Args:
            user: The User object that successfully logged in
        """
        nonlocal current_user
        
        # Check if database is connected before proceeding
        if not db_connected:
            # Try to reconnect to the database
            if not initialize_database():
                return
        
        current_user = user
        page.go("/")

    auth_page = AuthPage(page, on_login)

    page.on_route_change = route_change
    page.go("/login")


ft.app(target=main)