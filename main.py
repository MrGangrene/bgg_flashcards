import flet as ft
from database import Database
from pages.auth_page import AuthPage
from pages.main_page import MainPage
from pages.game_search_page import GameSearchPage
from pages.game_detail_page import GameDetailPage
from pages.create_flashcard_page import CreateFlashcardPage


def main(page: ft.Page):
    # Initialize database connection
    Database.initialize(
        minconn=1,
        maxconn=10,
        database="bgg_flashcards",
        user="stephen.van.cauwenberghe",
        password="password",
        host="localhost",
        port="5432"
    )

    page.title = "Board Game Flashcards"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0

    # Application state
    current_user = None

    # Function to handle route changes
    def route_change(route):
        page.views.clear()

        if not current_user and route.route != "/login":
            # Redirect to login if not authenticated
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

        elif route.route.startswith("/game/") and route.route.endswith("/create_flashcard"):
            # Create flashcard page
            # Extract the game_id from the route correctly
            path_parts = route.route.split("/")
            game_id = int(path_parts[-2])  # Get the second-to-last part which is the game_id
            create_page = CreateFlashcardPage(
                page=page,
                game_id=game_id,
                user_id=current_user.id,
                on_save=lambda: page.go(f"/game/{game_id}"),
                on_back=lambda: page.go(f"/game/{game_id}")
            )
            page.views.append(
                ft.View(
                    route=f"/game/{game_id}/create_flashcard",
                    controls=[create_page.build()],
                )
            )

        elif route.route.startswith("/game/"):
            # Game detail page with flashcards
            game_id = int(route.route.split("/")[-1])
            game_page = GameDetailPage(
                page=page,
                game_id=game_id,
                user_id=current_user.id,
                on_create_flashcard=lambda game_id: page.go(f"/game/{game_id}/create_flashcard"),
                on_back=lambda: page.go("/")
            )
            page.views.append(
                ft.View(
                    route=f"/game/{game_id}",
                    controls=[game_page.build()],
                )
            )
        elif route.route.startswith("/game/") and route.route.endswith("/create_flashcard"):
            # Create flashcard page
            game_id = int(route.route.split("/")[-2])
            create_page = CreateFlashcardPage(
                page=page,
                game_id=game_id,
                user_id=current_user.id,
                on_save=lambda: page.go(f"/game/{game_id}"),
                on_back=lambda: page.go(f"/game/{game_id}")
            )
            page.views.append(
                ft.View(
                    route=f"/game/{game_id}/create_flashcard",
                    controls=[create_page.build()],
                )
            )

        page.update()

    def logout():
        nonlocal current_user
        current_user = None
        page.go("/login")

    def on_login(user):
        nonlocal current_user
        current_user = user
        page.go("/")

    auth_page = AuthPage(page, on_login)

    page.on_route_change = route_change
    page.go("/login")


ft.app(target=main)