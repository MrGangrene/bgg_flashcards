import flet as ft
from models.user import User
from database import DatabaseError


class AuthPage:
    """This class handles the login and registration page.
    
    It allows users to create an account or log in to an existing one.
    """
    def __init__(self, page: ft.Page, on_login):
        """Create a new AuthPage.
        
        Args:
            page: The Flet page this will be displayed on
            on_login: Function to call when a user successfully logs in
        """
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
        """Create the login/register page UI.
        
        Returns:
            A Column containing the login form
        """
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

        self.message = ft.Text("", color=ft.Colors.RED)

        self.login_btn = ft.ElevatedButton(text="Login", on_click=self.login)
        self.register_btn = ft.TextButton(text="Register", on_click=self.toggle_auth_mode)

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
        """Switch between login and register modes.
        
        Args:
            e: The click event
        """
        self.is_login_mode = not self.is_login_mode

        if self.is_login_mode:
            self.login_btn.text = "Login"
            self.register_btn.text = "Register"
            self.email.visible = False
        else:
            self.login_btn.text = "Register"
            self.register_btn.text = "Already have an account? Login"
            self.email.visible = True

        self.message.value = ""
        self.page.update()

    def login(self, e):
        """Handle login or registration attempt.
        
        This checks credentials for login mode or creates a new account
        in register mode.
        
        Args:
            e: The submit event
        """
        username = self.username.value
        password = self.password.value

        if not username or not password:
            self.message.value = "Please fill all fields"
            self.page.update()
            return

        try:
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
        except DatabaseError:
            # Show a message about database connection error
            self.message.value = "Cannot connect to the database. Please try again later."
            self.page.update()
            # Redirect to database error page if it exists
            self.page.go("/db_error")