import flet as ft
from models.game import Game


class GameDetailPage:
    def __init__(self, page: ft.Page, game_id, user_id, on_create_flashcard, on_edit_flashcard, on_back):
        self.flashcards_view = None
        self.page = page
        self.game_id = game_id
        self.user_id = user_id
        self.on_create_flashcard = on_create_flashcard
        self.on_edit_flashcard = on_edit_flashcard
        self.on_back = on_back
        self.game = None
        self.user = None
        self.flashcards = []
        self.current_category = "Setup"
        self.categories = ["Setup", "Rules", "Points", "End of the game"]
        
        # Load user
        from models.user import User
        self.user = User.load_by_id(user_id)

    def load_data(self):
        self.game = Game.load_by_id(self.game_id)
        if not self.game:
            return False

        self.flashcards = self.game.get_flashcards()
        return True

    def change_category(self, category):
        self.current_category = category
        self.update_flashcards_view()

    def update_flashcards_view(self):
        self.flashcards_view.controls.clear()

        # Filter flashcards by current category
        category_flashcards = [f for f in self.flashcards if f.category == self.current_category]

        if not category_flashcards:
            self.flashcards_view.controls.append(
                ft.Container(
                    content=ft.Text(f"No flashcards for {self.current_category} yet."),
                    alignment=ft.alignment.center,
                )
            )
        else:
            for flashcard in category_flashcards:
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(flashcard.title, size=18, weight=ft.FontWeight.BOLD),
                                        ft.Row(
                                            [
                                                # Add edit button
                                                ft.IconButton(
                                                    icon=ft.icons.EDIT,
                                                    tooltip="Edit Flashcard",
                                                    on_click=lambda e, f_id=flashcard.id: self.on_edit_flashcard(f_id)
                                                ),
                                                # Add delete button
                                                ft.IconButton(
                                                    icon=ft.icons.DELETE,
                                                    tooltip="Delete Flashcard",
                                                    on_click=lambda e, f_id=flashcard.id: self.delete_flashcard(f_id)
                                                ),
                                            ],
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Divider(),
                                ft.Text(flashcard.content),
                            ],
                            spacing=10,
                        ),
                    ),
                    margin=10,
                )
                self.flashcards_view.controls.append(card)

        self.page.update()

    def delete_flashcard(self, flashcard_id):
        # Create confirmation dialog
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def confirm_delete(e):
            dialog.open = False
            self.page.update()

            # Delete the flashcard
            from models.flashcard import Flashcard
            Flashcard.delete_by_id(flashcard_id)

            # Reload flashcards
            self.flashcards = self.game.get_flashcards()
            self.update_flashcards_view()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Deletion"),
            content=ft.Text("Are you sure you want to delete this flashcard?"),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.TextButton("Delete", on_click=confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Show the dialog by adding it to the page
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
    def remove_game(self):
        # Create confirmation dialog
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def confirm_remove(e):
            dialog.open = False
            self.page.update()

            # Remove the game from user's saved games
            if self.user:
                self.user.unsave_game(self.game_id)
                # Navigate back to the main page
                self.on_back()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Removal"),
            content=ft.Text(f"Remove '{self.game.name}' from your saved games?"),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.TextButton("Remove", on_click=confirm_remove),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Show the dialog by adding it to the page
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def build(self):
        if not self.load_data():
            return ft.Column(
                [
                    ft.Text("Game not found"),
                    ft.ElevatedButton("Back", on_click=lambda e: self.on_back()),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

        # Create header with back button and delete button
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    tooltip="Back to My Games",
                    on_click=lambda e: self.on_back()
                ),
                ft.Text(self.game.name, size=24, weight=ft.FontWeight.BOLD),
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    tooltip="Remove from My Games",
                    on_click=lambda e: self.remove_game()
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Game info section
        game_info = ft.Row(
            [
                ft.Image(
                    src=self.game.image_path if self.game.image_path else "/placeholder.png",
                    width=150,
                    height=150,
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.Column(
                    [
                        ft.Text(f"Rating: {self.game.avg_rating}"),
                        ft.Text(f"Players: {self.game.min_players if self.game.min_players == self.game.max_players else f'{self.game.min_players}-{self.game.max_players}'}"),
                        ft.ElevatedButton(
                            text="Create Flashcard",
                            icon=ft.icons.ADD,
                            on_click=lambda e: self.on_create_flashcard(self.game_id)
                        )
                    ],
                    spacing=10,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
        )

        # Category tabs
        tabs = ft.Tabs(
            selected_index=0,
            on_change=lambda e: self.change_category(self.categories[e.control.selected_index]),
            tabs=[ft.Tab(text=category) for category in self.categories],
        )

        # Flashcards view
        self.flashcards_view = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        # Initialize flashcards view with first category
        self.update_flashcards_view()

        return ft.Column(
            [
                header,
                ft.Divider(),
                game_info,
                ft.Divider(),
                tabs,
                self.flashcards_view,
            ],
            expand=True,
            spacing=10,
        )