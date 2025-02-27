import flet as ft
from models.user import User


class AuthPage:
    def __init__(self, page: ft.Page, on_login):
        self.is_login_mode = None
        self.register_btn = None
        self.login_btn = None
        self.message = None
        self.email = None
        self.password = None
        self.username = None
        self.page = page
        self.on_login = on_login

    def build(self):
        self.username = ft.TextField(
            label="Username", 
            autofocus=True, 
            width=300,
            on_submit=self.login
        )
        self.password = ft.TextField(
            label="Password", 
            password=True, 
            width=300,
            on_submit=self.login
        )
        self.email = ft.TextField(
            label="Email", 
            width=300, 
            visible=False,
            on_submit=self.login
        )  # For registration

        self.message = ft.Text("", color=ft.colors.RED)

        self.login_btn = ft.ElevatedButton(text="Login", on_click=self.login)
        self.register_btn = ft.TextButton(text="Need an account? Register", on_click=self.toggle_auth_mode)

        self.is_login_mode = True

        return ft.Column(
            [
                ft.Text("Board Game Flashcards", size=30, weight=ft.FontWeight.BOLD),
                self.message,
                self.username,
                self.email,
                self.password,
                ft.Row([self.login_btn, self.register_btn], alignment=ft.MainAxisAlignment.CENTER),
            ],
            width=400,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def toggle_auth_mode(self, e):
        self.is_login_mode = not self.is_login_mode

        if self.is_login_mode:
            self.login_btn.text = "Login"
            self.register_btn.text = "Need an account? Register"
            self.email.visible = False
        else:
            self.login_btn.text = "Register"
            self.register_btn.text = "Already have an account? Login"
            self.email.visible = True

        self.message.value = ""
        self.page.update()

    def login(self, e):
        username = self.username.value
        password = self.password.value

        if not username or not password:
            self.message.value = "Please fill all fields"
            self.page.update()
            return

        if self.is_login_mode:
            user = User.load_by_username(username)
            if user and user.verify_password(password):
                self.on_login(user)
            else:
                self.message.value = "Invalid username or password"
                self.page.update()
        else:
            email = self.email.value
            if not email:
                self.message.value = "Please fill all fields"
                self.page.update()
                return

            # Check if username already exists
            existing_user = User.load_by_username(username)
            if existing_user:
                self.message.value = "Username already exists"
                self.page.update()
                return

            # Create new user
            user = User(username, email, password)
            user.save_to_db()
            self.message.value = "Registration successful! You can now login."
            self.toggle_auth_mode(None)