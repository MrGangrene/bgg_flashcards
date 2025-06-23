import flet as ft
from models.user import User


class MainPage:
    """This class represents the main page of the application.
    
    It displays the user's saved games and allows them to select a game
    or add a new one.
    """
    def __init__(self, page: ft.Page, user: User | None, on_game_select, on_add_game, on_logout):
        """Create a new MainPage.
        
        Args:
            page: The Flet page this will be displayed on
            user: The currently logged in user
            on_game_select: Function to call when a game is selected
            on_add_game: Function to call when the add game button is clicked
            on_logout: Function to call when the logout button is clicked
        """
        self.page = page
        self.user = user
        self.on_game_select = on_game_select
        self.on_add_game = on_add_game
        self.on_logout = on_logout
        self.games = []

    def load_games(self):
        """Load the user's saved games from the database.
        
        This gets all games saved by the user and sorts them alphabetically.
        """
        self.games = self.user.get_saved_games()
        # Sort games alphabetically by name
        self.games.sort(key=lambda game: game.name.lower())

    def build(self):
        """Create the main page UI.
        
        Returns:
            A Column containing the header and game grid
        """
        self.load_games()

        # Create header with logout button
        header = ft.Row(
            [
                ft.Text(f"Welcome, {self.user.username}!", size=20, weight=ft.FontWeight.BOLD),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Logout",
                    on_click=lambda e: self.on_logout()
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # Create game grid
        game_grid = ft.GridView(
            expand=1,
            runs_count=3,
            max_extent=300,
            child_aspect_ratio=1.0,
            spacing=10,
            run_spacing=10,
        )

        # Add games to grid
        for game in self.games:
            # Wrap Card with GestureDetector for click handling
            game_card = ft.GestureDetector(
                on_tap=lambda e, game_id=game.id: self.on_game_select(game_id),
                content=ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Image(
                                    src=game.image_path if game.image_path else "/placeholder.png",
                                    width=150,
                                    height=100,
                                    fit=ft.ImageFit.CONTAIN,
                                ),
                                ft.Text(game.name, size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                                ft.Text(f"Rating: {game.avg_rating}", size=12),
                                ft.Text(f"Players: {game.min_players if game.min_players == game.max_players else f'{game.min_players}-{game.max_players}'}", size=12),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        width=180,
                        height=180,
                        padding=10,
                    ),
                )
            )
            game_grid.controls.append(game_card)

        # Add "Add Game" card - also wrapped with GestureDetector
        add_game_card = ft.GestureDetector(
            on_tap=lambda e: self.on_add_game(),
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=50),
                            ft.Text("Add New Game", size=16, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=180,
                    height=180,
                    padding=10,
                ),
            )
        )
        game_grid.controls.append(add_game_card)

        return ft.Column(
            [
                header,
                ft.Divider(),
                ft.Text("My Saved Games", size=24, weight=ft.FontWeight.BOLD),
                game_grid,
            ],
            expand=True,
            spacing=20,
        )