import flet as ft
from models.game import Game
from models.flashcard import Flashcard


class EditFlashcardPage:
    def __init__(self, page: ft.Page, flashcard_id, on_save, on_back):
        self.title_field = None
        self.content_field = None
        self.category_dropdown = None
        self.message = None
        self.page = page
        self.flashcard_id = flashcard_id
        self.on_save = on_save
        self.on_back = on_back
        self.flashcard = None
        self.game = None
        self.categories = ["Setup", "Rules", "Points", "End of the game"]

    def load_data(self):
        self.flashcard = Flashcard.load_by_id(self.flashcard_id)
        if not self.flashcard:
            return False
            
        self.game = Game.load_by_id(self.flashcard.game_id)
        return self.game is not None

    def update_flashcard(self, e):
        title = self.title_field.value
        content = self.content_field.value
        category = self.category_dropdown.value

        if not title or not content or not category:
            self.message.value = "Please fill all fields"
            self.page.update()
            return

        self.flashcard.title = title
        self.flashcard.content = content
        self.flashcard.category = category
        self.flashcard.update()

        self.on_save()

    def build(self):
        if not self.load_data():
            return ft.Column(
                [
                    ft.Text("Flashcard not found"),
                    ft.ElevatedButton("Back", on_click=lambda e: self.on_back()),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

        # Create header with back button
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    tooltip="Back to Game",
                    on_click=lambda e: self.on_back()
                ),
                ft.Text(f"Edit Flashcard for {self.game.name}", size=20, weight=ft.FontWeight.BOLD),
            ]
        )

        self.message = ft.Text("", color=ft.colors.RED)

        # Create form fields with existing flashcard data
        self.category_dropdown = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(category) for category in self.categories],
            value=self.flashcard.category,
            width=400,
        )

        self.title_field = ft.TextField(
            label="Title",
            value=self.flashcard.title,
            width=400,
        )

        self.content_field = ft.TextField(
            label="Content",
            value=self.flashcard.content,
            multiline=True,
            min_lines=5,
            max_lines=10,
            width=400,
        )

        save_button = ft.ElevatedButton("Update Flashcard", on_click=self.update_flashcard)

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