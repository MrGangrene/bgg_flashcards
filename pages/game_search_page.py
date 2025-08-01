"""Game Search Page Module.

This module contains the GameSearchPage class which provides the UI for searching
and discovering board games from both local database and BoardGameGeek API.

The page supports:
- Real-time search with immediate local results
- Background BGG API integration
- Both name-based and ID-based searches
- Game saving to user collections
- Expansion discovery and management
- Background task management and cancellation
"""

import flet as ft
from models.game import Game
from models.user import User
from utils.background_tasks import background_manager


class GameSearchPage:
    """UI page for searching and discovering board games.
    
    This page provides a comprehensive game search interface that combines
    local database searches with real-time BoardGameGeek API integration.
    It supports both immediate local results and background BGG fetching.
    
    Search Types:
        - Name search: Searches by game name in local DB + BGG API
        - ID search: Direct BGG ID lookup with background name search
        
    Features:
        - Immediate local search results
        - Background BGG API integration with progress indicators
        - Game saving to user collections
        - Expansion discovery and display
        - Task cancellation for interrupted searches
        
    Attributes:
        page (ft.Page): The Flet page object
        user (User): Current logged-in user
        on_save_game (callable): Callback after game is saved
        on_back (callable): Callback when user goes back
        local_results (list): Games from local database
        local_expansions (list): Expansions from local database
        bgg_results (list): Games from BGG API
        is_loading (bool): Whether background search is in progress
        
    UI Components:
        - search_field: Text input for search queries
        - results_list: Display area for search results
    """
    def __init__(self, page: ft.Page, user: User | None, on_save_game, on_back):
        """Initialize the GameSearchPage.
        
        Args:
            page (ft.Page): The Flet page object
            user (User, optional): Current logged-in user (None if not logged in)
            on_save_game (callable): Callback function called after game is saved
            on_back (callable): Callback function called when user goes back
        """
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

    def search_games(self, _):
        """Search for games based on the query in the search field.
        
        Determines search type (ID vs name) and delegates to appropriate handler.
        Cancels any existing background searches before starting new one.
        
        Args:
            _: The button click or enter key event (unused)
            
        Search Logic:
            - Numeric query: Treated as BGG ID search
            - Text query: Treated as name search
        """
        query = self.search_field.value
        if query:
            # Check if it's an ID search
            is_id_search = query.isdigit()
            
            if is_id_search:
                # For ID search, show local results first, then fetch from BGG in background
                self.show_immediate_results_for_id(query)
            else:
                # For name search, show local results first, then fetch from BGG in background
                self.show_immediate_results_for_name(query)
    
    def show_immediate_results_for_id(self, game_id):
        """Handle BGG ID searches with immediate local results and background fetch.
        
        For ID searches, prioritizes local database results and shows them immediately,
        then refreshes with updated BGG data in the background.
        
        Args:
            game_id (str): The BGG ID to search for
            
        Process:
            1. Check local database for existing game
            2. If found: Show immediately + background refresh
            3. If not found: Show loading + background fetch
            4. Trigger expansion search in background
        """
        # First, check if we already have this game locally
        existing_game = Game.load_by_id(game_id)
        
        if existing_game:
            # Show existing local data immediately
            self.local_results = [existing_game]
            # Get local expansions too
            results = Game.search_by_name(existing_game.name)
            self.local_expansions = results["local_expansions"]
            self.bgg_results = []
            
            self.is_loading = False
            self.update_results_list()
            
            # Also refresh from BGG in background to get any new data
            def on_bgg_complete(games):
                # Refresh results after background fetch
                if games:
                    self.local_results = games
                    # Get updated expansions
                    background_manager.fetch_expansions_in_background(
                        game_id, 
                        lambda exps: self.update_expansions_after_background(exps)
                    )
            
            background_manager.fetch_bgg_data_in_background(f"bgg_id_{game_id}", on_bgg_complete)
            
        else:
            # No local data, show loading and fetch from BGG
            self.is_loading = True
            self.update_loading_state()
            
            def on_fetch_complete(games):
                if games:
                    self.local_results = games
                    # Also fetch expansions
                    background_manager.fetch_expansions_in_background(
                        game_id,
                        lambda exps: self.update_expansions_after_background(exps)
                    )
                else:
                    self.local_results = []
                    self.local_expansions = []
                
                self.bgg_results = []
                self.is_loading = False
                self.update_results_list()
            
            # For new games, fetch in background and show placeholder initially
            background_manager.fetch_bgg_data_in_background(f"bgg_id_{game_id}", on_fetch_complete)
    
    def show_immediate_results_for_name(self, query):
        """Handle name searches with immediate local results and background BGG fetch.
        
        Shows local database results immediately, then enriches with BGG API
        results in the background for a responsive user experience.
        
        Args:
            query (str): The game name to search for
            
        Process:
            1. Search local database immediately
            2. Display local results
            3. Start background BGG API search
            4. Update results when BGG search completes
        """
        # Show local results immediately
        results = Game.search_by_name(query)
        self.local_results = results["local_games"]
        self.local_expansions = results["local_expansions"]
        self.bgg_results = []
        
        self.is_loading = False
        self.update_results_list()
        
        # Add subtle indicator that we're refreshing in background
        self.add_background_indicator()
        
        # Fetch fresh data from BGG in background
        def on_bgg_immediate(basic_games):
            """Called immediately with basic BGG search results."""
            if basic_games:
                print(f"📋 Received {len(basic_games)} immediate basic results")
                # Show basic results immediately
                base_games = [g for g in basic_games if not g.is_expansion]
                expansions = [g for g in basic_games if g.is_expansion]
                
                # Merge with existing local results (avoid duplicates)
                existing_ids = {g.id for g in self.local_results}
                new_base_games = [g for g in base_games if g.id not in existing_ids]
                
                existing_exp_ids = {g.id for g in self.local_expansions}  
                new_expansions = [g for g in expansions if g.id not in existing_exp_ids]
                
                self.local_results.extend(new_base_games)
                self.local_expansions.extend(new_expansions)
                self.update_results_list()
        
        def on_bgg_complete(detailed_games):
            """Called when detailed BGG data is ready."""
            if detailed_games:
                # Replace ALL existing games with detailed versions (both database and search-only)
                detailed_ids = {g.id for g in detailed_games}
                
                # Remove any existing games that match the detailed games (by ID)
                self.local_results = [g for g in self.local_results if g.id not in detailed_ids]
                self.local_expansions = [g for g in self.local_expansions if g.id not in detailed_ids]
                
                # Add the updated detailed games (these have been saved to database by get_bgg_game_details)
                base_games = [g for g in detailed_games if not g.is_expansion]
                expansions = [g for g in detailed_games if g.is_expansion]
                
                self.local_results.extend(base_games)
                self.local_expansions.extend(expansions)
            else:
                # If no BGG results, refresh local search in case something was updated
                updated_results = Game.search_by_name(query)
                self.local_results = updated_results["local_games"]
                self.local_expansions = updated_results["local_expansions"]
            
            self.remove_background_indicator()
            self.update_results_list()
        
        background_manager.fetch_bgg_data_in_background(query, on_bgg_complete, on_bgg_immediate)
    
    def update_expansions_after_background(self, expansions):
        """Update expansions list after background fetch."""
        if expansions:
            self.local_expansions.extend(expansions)
            # Remove duplicates based on ID
            seen_ids = set()
            unique_expansions = []
            for exp in self.local_expansions:
                if exp.id not in seen_ids:
                    unique_expansions.append(exp)
                    seen_ids.add(exp.id)
            self.local_expansions = unique_expansions
            self.update_results_list()
    
    def add_background_indicator(self):
        """Add a subtle indicator that background fetching is happening."""
        if hasattr(self, 'results_list') and self.results_list.controls:
            indicator = ft.Container(
                content=ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text("Refreshing from BoardGameGeek...", size=12, color=ft.Colors.BLUE_600)
                ]),
                padding=5,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=5,
                margin=ft.margin.only(bottom=10)
            )
            self.results_list.controls.insert(0, indicator)
            self.page.update()
    
    def remove_background_indicator(self):
        """Remove the background fetching indicator."""
        if hasattr(self, 'results_list') and self.results_list.controls:
            # Remove the first control if it's our indicator
            if (self.results_list.controls and 
                isinstance(self.results_list.controls[0], ft.Container) and
                self.results_list.controls[0].bgcolor == ft.Colors.BLUE_50):
                self.results_list.controls.pop(0)
                self.page.update()

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
        def create_game_item(game_data):
            # Create subtitle with available game details
            subtitle_parts = []
            
            # Year published (when available)
            if hasattr(game_data, 'yearpublished') and game_data.yearpublished:
                subtitle_parts.append(f"({game_data.yearpublished})")
                
            # Rating - show actual value or nothing
            if game_data.avg_rating and game_data.avg_rating > 0:
                subtitle_parts.append(f"Rating: {game_data.avg_rating}")
            
            # Player count - show if we have valid data (including 1 player games)
            if (hasattr(game_data, 'min_players') and hasattr(game_data, 'max_players') and
                game_data.min_players is not None and game_data.max_players is not None and 
                game_data.min_players >= 1 and game_data.max_players >= 1):
                player_count = f"Players: {game_data.min_players if game_data.min_players == game_data.max_players else f'{game_data.min_players}-{game_data.max_players}'}"
                subtitle_parts.append(player_count)
            
            subtitle_text = " • ".join(subtitle_parts)
            
            return ft.ListTile(
                leading=ft.Image(
                    width=50,
                    height=50,
                    fit=ft.ImageFit.CONTAIN,
                    **game_data.get_image_src()
                ),
                title=ft.Row([
                    ft.Text(game_data.name),
                    ft.Text(f"ID: {game_data.id}", size=12, color=ft.Colors.GREY_600, italic=True)
                ]),
                subtitle=ft.Text(subtitle_text),
                trailing=ft.IconButton(
                    icon=ft.Icons.ADD,
                    tooltip="Add to my games",
                    on_click=lambda e, game_id=game_data.id: self.save_game(game_id)
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