import flet as ft
from models.game import Game
from models.user import User


class GameSearchPage:
    def __init__(self, page: ft.Page, user: User, on_save_game, on_back):
        self.page = page
        self.user = user
        self.on_save_game = on_save_game
        self.on_back = on_back
        self.search_results = []

    def search_games(self, e):
        query = self.search_field.value
        if query:
            self.search_results = Game.search_by_name(query)
            self.update_results_list()

    def update_results_list(self):
        self.results_list.controls.clear()

        for game in self.search_results:
            game_item = ft.ListTile(
                leading=ft.Image(
                    src=game.image_path if game.image_path else "/placeholder.png",
                    width=50,
                    height=50,
                    fit=ft.ImageFit.CONTAIN,
                ),
                title=ft.Text(game.name),
                subtitle=ft.Text(f"Rating: {game.avg_rating}/10 • Players: {game.min_players}-{game.max_players}"),
                trailing=ft.IconButton(
                    icon=ft.icons.ADD,
                    tooltip="Add to my games",
                    on_click=lambda e, game_id=game.id: self.save_game(game_id)
                )
            )
            self.results_list.controls.append(game_item)

        if not self.search_results:
            self.results_list.controls.append(ft.Text("No games found"))

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
                ft.Divider(),
                self.results_list,
            ],
            expand=True,
            spacing=10,
        )