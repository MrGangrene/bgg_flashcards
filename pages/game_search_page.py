import flet as ft
from models.game import Game
from models.user import User


class GameSearchPage:
    def __init__(self, page: ft.Page, user: User, on_save_game, on_back):
        self.results_list = None
        self.search_field = None
        self.page = page
        self.user = user
        self.on_save_game = on_save_game
        self.on_back = on_back
        self.search_results = []
        self.is_loading = False

    def search_games(self, e):
        query = self.search_field.value
        if query:
            self.is_loading = True
            self.update_loading_state()
            
            # Get search results (includes BGG API call if local DB has no matches)
            self.search_results = Game.search_by_name(query)
            
            self.is_loading = False
            self.update_results_list()

    def update_loading_state(self):
        self.results_list.controls.clear()
        
        if self.is_loading:
            self.results_list.controls.append(
                ft.Column([
                    ft.ProgressRing(),
                    ft.Text("Searching local database and BoardGameGeek..."),
                ], alignment=ft.MainAxisAlignment.CENTER)
            )
        
        self.page.update()

    def update_results_list(self):
        self.results_list.controls.clear()

        # Show source (database or BGG API)
        for i, game in enumerate(self.search_results):
            source_text = ""
            if hasattr(game, '_source'):
                source_text = f" • From: {game._source}"
            
            game_item = ft.ListTile(
                leading=ft.Image(
                    src=game.image_path if game.image_path else "/placeholder.png",
                    width=50,
                    height=50,
                    fit=ft.ImageFit.CONTAIN,
                ),
                title=ft.Text(game.name),
                subtitle=ft.Text(f"Rating: {game.avg_rating} • Players: {game.min_players if game.min_players == game.max_players else f'{game.min_players}-{game.max_players}'}{source_text}"),
                trailing=ft.IconButton(
                    icon=ft.icons.ADD,
                    tooltip="Add to my games",
                    on_click=lambda e, game_id=game.id: self.save_game(game_id)
                )
            )
            self.results_list.controls.append(game_item)

        if not self.search_results:
            self.results_list.controls.append(
                ft.Column([
                    ft.Text("No games found", size=16),
                    ft.Text("We searched both your database and BoardGameGeek", size=12),
                ], alignment=ft.MainAxisAlignment.CENTER)
            )

        self.page.update()

    def save_game(self, game_id):
        self.user.save_game(game_id)
        self.on_save_game()

    def build(self):
        # Create header with back button
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    tooltip="Back to My Games",
                    on_click=lambda e: self.on_back()
                ),
                ft.Text("Search Games", size=20, weight=ft.FontWeight.BOLD),
            ]
        )

        # Create search field
        self.search_field = ft.TextField(
            label="Game Name",
            hint_text="Enter a game name to search",
            on_submit=self.search_games,
            autofocus=True,
            expand=True
        )

        search_button = ft.ElevatedButton(
            text="Search",
            on_click=self.search_games
        )

        search_row = ft.Row(
            [self.search_field, search_button],
            alignment=ft.MainAxisAlignment.CENTER,
        )
        
        # Info text about BGG integration
        bgg_info = ft.Text(
            "Searches both locally and on BoardGameGeek",
            size=12, 
            italic=True,
            text_align=ft.TextAlign.CENTER
        )

        # Results list
        self.results_list = ft.ListView(
            expand=True,
            spacing=10,
        )

        return ft.Column(
            [
                header,
                ft.Divider(),
                search_row,
                bgg_info,
                ft.Divider(),
                self.results_list,
            ],
            expand=True,
            spacing=10,
        )