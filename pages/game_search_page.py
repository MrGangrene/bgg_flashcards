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
        self.local_results = []
        self.local_expansions = []
        self.bgg_results = []
        self.is_loading = False

    def search_games(self, e):
        query = self.search_field.value
        if query:
            self.is_loading = True
            self.update_loading_state()
            
            # First check if it's an ID search
            is_id_search = query.isdigit()
            
            # If not an ID search, update local database from BGG first
            if not is_id_search:
                # Update message to show we're fetching from BGG
                self.results_list.controls.clear()
                self.results_list.controls.append(
                    ft.Column([
                        ft.ProgressRing(),
                        ft.Text("Updating local database from BoardGameGeek..."),
                    ], alignment=ft.MainAxisAlignment.CENTER)
                )
                self.page.update()
                
                # Fetch and import BGG data to update local database
                Game.search_bgg_api(query)
            
            # Now search the local database (which should include any new BGG data)
            self.results_list.controls.clear()
            self.results_list.controls.append(
                ft.Column([
                    ft.ProgressRing(),
                    ft.Text("Retrieving games from database..."),
                ], alignment=ft.MainAxisAlignment.CENTER)
            )
            self.page.update()
            
            # Get search results (now with updated database)
            results = Game.search_by_name(query)
            self.local_results = results["local_games"]
            self.local_expansions = results["local_expansions"]
            self.bgg_results = []  # We're not showing BGG results separately
            
            self.is_loading = False
            self.update_results_list()

    def update_loading_state(self):
        self.results_list.controls.clear()
        
        if self.is_loading:
            self.results_list.controls.append(
                ft.Column([
                    ft.ProgressRing(),
                    ft.Text("Searching for games..."),
                ], alignment=ft.MainAxisAlignment.CENTER)
            )
        
        self.page.update()

    def update_results_list(self):
        self.results_list.controls.clear()
        
        # Helper function to create a game list item
        def create_game_item(game):
            # Create subtitle with available game details
            subtitle_parts = []
            
            # Year published (when available)
            if hasattr(game, 'yearpublished') and game.yearpublished:
                subtitle_parts.append(f"({game.yearpublished})")
                
            # Rating
            subtitle_parts.append(f"Rating: {game.avg_rating}")
            
            # Player count
            player_count = f"Players: {game.min_players if game.min_players == game.max_players else f'{game.min_players}-{game.max_players}'}"
            subtitle_parts.append(player_count)
            
            subtitle_text = " • ".join(subtitle_parts)
            
            return ft.ListTile(
                leading=ft.Image(
                    src=game.image_path if game.image_path else "/placeholder.png",
                    width=50,
                    height=50,
                    fit=ft.ImageFit.CONTAIN,
                ),
                title=ft.Row([
                    ft.Text(game.name),
                    ft.Text(f"ID: {game.id}", size=12, color=ft.Colors.GREY_600, italic=True)
                ]),
                subtitle=ft.Text(subtitle_text),
                trailing=ft.IconButton(
                    icon=ft.Icons.ADD,
                    tooltip="Add to my games",
                    on_click=lambda e, game_id=game.id: self.save_game(game_id)
                )
            )

        # Display base games first (if any)
        if self.local_results:
            self.results_list.controls.append(
                ft.Text(f"Games Found ({len(self.local_results)})", 
                        size=16, weight=ft.FontWeight.BOLD)
            )
            
            for game in self.local_results:
                game_item = create_game_item(game)
                self.results_list.controls.append(game_item)
        
        # Display expansions (if any)
        if self.local_expansions:
            # Add separator between games and expansions
            if self.local_results:
                self.results_list.controls.append(ft.Divider())
                
            self.results_list.controls.append(
                ft.Text(f"Expansions Found ({len(self.local_expansions)})", 
                        size=16, weight=ft.FontWeight.BOLD)
            )
            
            for expansion in self.local_expansions:
                expansion_item = create_game_item(expansion)
                self.results_list.controls.append(expansion_item)
        

        # Show message if no results found at all
        if not self.local_results and not self.local_expansions:
            self.results_list.controls.clear()
            self.results_list.controls.append(
                ft.Column([
                    ft.Text("No games found", size=16),
                    ft.Text("Try searching by game name or BoardGameGeek ID", size=12),
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
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Back to My Games",
                    on_click=lambda e: self.on_back()
                ),
                ft.Text("Search Games", size=20, weight=ft.FontWeight.BOLD),
            ]
        )

        # Create search field
        self.search_field = ft.TextField(
            label="Game Search",
            hint_text="Enter a game name or BGG ID to search",
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
        
        # Info text about search capabilities
        search_info = ft.Text(
            "Search by game name or BoardGameGeek ID number",
            size=12, 
            italic=True,
            text_align=ft.TextAlign.CENTER
        )

        # Results list
        self.results_list = ft.ListView(
            expand=True,
            spacing=10,
            divider_thickness=1,
        )

        return ft.Column(
            [
                header,
                ft.Divider(),
                search_row,
                search_info,
                ft.Divider(),
                self.results_list,
            ],
            expand=True,
            spacing=10,
        )