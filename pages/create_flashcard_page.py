"""Create Flashcard Page Module.

This module contains the CreateFlashcardPage class which provides the UI
for creating new flashcards and editing existing ones.

The page supports:
- Creating new flashcards for a specific game
- Editing existing flashcards
- Category selection and organization
- Privacy settings for flashcards
- Content appending to existing flashcards with same title
"""

import flet as ft
from models.game import Game
from models.flashcard import Flashcard


class CreateFlashcardPage:
    """UI page for creating and editing flashcards.
    
    This page can operate in two modes:
    1. Create mode: Creating a new flashcard for a game
    2. Edit mode: Editing an existing flashcard
    
    The page includes form fields for title, content, category selection,
    and privacy settings. It handles both new flashcard creation and
    content appending to existing flashcards with matching titles.
    
    Attributes:
        page (ft.Page): The Flet page object
        game_id (int): ID of the game this flashcard is for
        user_id (int): ID of the user creating/editing the flashcard
        flashcard_id (int, optional): ID of flashcard being edited (None for create mode)
        default_category (str, optional): Default category to select
        on_save (callable): Callback function called after successful save
        on_back (callable): Callback function called when user goes back
        is_edit_mode (bool): True if editing existing flashcard, False for new
        categories (list): Available flashcard categories
        
    UI Components:
        - title_field: Text input for flashcard title
        - content_field: Multi-line text input for flashcard content
        - category_dropdown: Dropdown for category selection
        - private_checkbox: Checkbox for privacy setting
        - message: Text component for user feedback
    """
    def __init__(self, page: ft.Page, game_id=None, user_id=None, flashcard_id=None, default_category=None, on_save=None, on_back=None):
        """Initialize the CreateFlashcardPage.
        
        Args:
            page (ft.Page): The Flet page object
            game_id (int, optional): ID of the game for new flashcards
            user_id (int, optional): ID of the user creating the flashcard
            flashcard_id (int, optional): ID of flashcard to edit (triggers edit mode)
            default_category (str, optional): Default category to select
            on_save (callable, optional): Callback function after successful save
            on_back (callable, optional): Callback function when user goes back
            
        Note:
            Either (game_id, user_id) for create mode or id for edit mode
            must be provided. Edit mode will load game_id and user_id from the flashcard.
        """
        self.content_field = None
        self.category_dropdown = None
        self.title_field = None
        self.private_checkbox = None
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
        """Load required data based on the page mode.
        
        In edit mode: Loads the flashcard and associated game data
        In create mode: Loads the game data
        
        Returns:
            bool: True if data loaded successfully, False otherwise
            
        Note:
            This method must be called before building the UI to ensure
            all required data is available.
        """
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
        
        Handles both new flashcard creation and updates to existing flashcards.
        For new flashcards with duplicate titles, appends content to existing flashcard.
        
        Args:
            _: The button click event (unused)
            
        Behavior:
            - Edit mode: Updates the existing flashcard
            - Create mode with new title: Creates new flashcard
            - Create mode with existing title: Appends content to existing flashcard
            
        Validation:
            Ensures all required fields (title, content, category) are filled
            before attempting to save.
        """
        title = self.title_field.value
        content = self.content_field.value
        category = self.category_dropdown.value
        is_private = self.private_checkbox.content.value

        if not title or not content or not category:
            self.message.value = "Please fill all fields"
            self.page.update()
            return

        if self.is_edit_mode:
            # Update existing flashcard
            self.flashcard.title = title
            self.flashcard.content = content
            self.flashcard.category = category
            self.flashcard.is_private = is_private
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
                existing_flashcard.is_private = is_private
                existing_flashcard.update()
                self.message.value = "Flashcard content appended successfully"
                self.message.color = ft.Colors.GREEN
            else:
                # Create new flashcard
                flashcard = Flashcard(self.game_id, self.user_id, category, title, content, is_private=is_private)
                flashcard.save_to_db()
                self.message.value = "New flashcard created successfully"
                self.message.color = ft.Colors.GREEN
        
        self.page.update()
        self.on_save()

    def build(self):
        """Build and return the UI for the create/edit flashcard page.
        
        Creates the complete UI including header, form fields, and save button.
        Handles both create and edit modes with appropriate field pre-population.
        
        Returns:
            ft.Column: The main UI column containing all page elements
            
        UI Structure:
            - Header with back button and page title
            - Form fields (category, title, content, privacy)
            - Save/Update button
            - Error/success message display
            
        Error Handling:
            If required data fails to load, displays error message with back button.
        """
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

        self.private_checkbox = ft.Container(
            content=ft.Checkbox(
                label="Private Entry",
                value=self.flashcard.is_private if self.is_edit_mode else False,
                tooltip="When checked, only you can see this flashcard",
            ),
            alignment=ft.alignment.center,
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
                self.private_checkbox,
                save_button,
            ],
            expand=True,
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )