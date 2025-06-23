import flet as ft
from models.game import Game
from models.flashcard import Flashcard


class CreateFlashcardPage:
    def __init__(self, page: ft.Page, game_id=None, user_id=None, flashcard_id=None, default_category=None, on_save=None, on_back=None):
        self.content_field = None
        self.category_dropdown = None
        self.title_field = None
        self.message = None
        self.page = page
        self.game_id = game_id
        self.user_id = user_id
        self.flashcard_id = flashcard_id
        self.default_category = default_category
        self.on_save = on_save
        self.on_back = on_back
        self.game = None
        self.flashcard = None
        self.is_edit_mode = flashcard_id is not None
        self.categories = ["Setup", "Rules", "Events", "Points", "End of the game", "Notes"]

    def load_data(self):
        if self.is_edit_mode:
            # Edit mode: Load flashcard and game data
            self.flashcard = Flashcard.load_by_id(self.flashcard_id)
            if not self.flashcard:
                return False
                
            self.game_id = self.flashcard.game_id
            self.user_id = self.flashcard.user_id
            self.game = Game.load_by_id(self.game_id)
            return self.game is not None
        else:
            # Create mode: Load game data
            self.game = Game.load_by_id(self.game_id)
            return self.game is not None

    def save_flashcard(self, _):
        """Save the flashcard to the database.
        
        Args:
            _: The button click event (unused)
        """
        title = self.title_field.value
        content = self.content_field.value
        category = self.category_dropdown.value

        if not title or not content or not category:
            self.message.value = "Please fill all fields"
            self.page.update()
            return

        if self.is_edit_mode:
            # Update existing flashcard
            self.flashcard.title = title
            self.flashcard.content = content
            self.flashcard.category = category
            self.flashcard.update()
            self.message.value = "Flashcard updated successfully"
            self.message.color = ft.Colors.GREEN
        else:
            # Check if a flashcard with this title already exists for this game and user
            existing_flashcard = Flashcard.find_by_game_user_title(self.game_id, self.user_id, title)
            
            if existing_flashcard:
                # Append to existing flashcard with an empty line between old and new content
                updated_content = existing_flashcard.content + "\n\n" + content
                existing_flashcard.content = updated_content
                existing_flashcard.category = category
                existing_flashcard.update()
                self.message.value = "Flashcard content appended successfully"
                self.message.color = ft.Colors.GREEN
            else:
                # Create new flashcard
                flashcard = Flashcard(self.game_id, self.user_id, category, title, content)
                flashcard.save_to_db()
                self.message.value = "New flashcard created successfully"
                self.message.color = ft.Colors.GREEN
        
        self.page.update()
        self.on_save()

    def build(self):
        if not self.load_data():
            error_message = "Flashcard not found" if self.is_edit_mode else "Game not found"
            return ft.Column(
                [
                    ft.Text(error_message),
                    ft.ElevatedButton("Back", on_click=lambda e: self.on_back()),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

        # Create header with back button
        page_title = f"Edit Flashcard for {self.game.name}" if self.is_edit_mode else f"Create Flashcard for {self.game.name}"
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Back to Game",
                    on_click=lambda e: self.on_back()
                ),
                ft.Text(page_title, size=20, weight=ft.FontWeight.BOLD),
            ]
        )

        self.message = ft.Text("", color=ft.Colors.RED)

        # Create form fields
        self.category_dropdown = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(category) for category in self.categories],
            value=self.flashcard.category if self.is_edit_mode else (self.default_category if self.default_category in self.categories else self.categories[0]),
            width=400,
        )

        self.title_field = ft.TextField(
            label="Title",
            hint_text="Enter flashcard title",
            value=self.flashcard.title if self.is_edit_mode else "",
            width=400,
        )

        self.content_field = ft.TextField(
            label="Content",
            hint_text="Enter flashcard content",
            value=self.flashcard.content if self.is_edit_mode else "",
            multiline=True,
            min_lines=5,
            max_lines=10,
            width=400,
        )

        button_text = "Update Flashcard" if self.is_edit_mode else "Save Flashcard"
        save_button = ft.ElevatedButton(button_text, on_click=self.save_flashcard)

        return ft.Column(
            [
                header,
                ft.Divider(),
                self.message,
                self.category_dropdown,
                self.title_field,
                self.content_field,
                save_button,
            ],
            expand=True,
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )