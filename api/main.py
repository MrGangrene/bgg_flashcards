from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from contextlib import asynccontextmanager
import uvicorn

from database import Database, DatabaseError, CursorFromConnectionPool
from api.schemas import (
    User, UserCreate, Token, Game, GameSearch,
    UserGameOperation, Flashcard, FlashcardCreate, GameSearchResults
)
from api.auth import (
    get_current_user, authenticate_user, create_access_token,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)

# Define lifespan context manager for app startup/shutdown events
@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: Initialize database connection
    try:
        Database.initialize(
            minconn=1,
            maxconn=10,
            database="bgg_flashcards",
            user="stephenvc",
            password="UsCAxzFPGT217HHjXvEQCAThUU8ciZ5Z8gAH9FxxKI3e5qzBQn",
            host="10.0.0.150",
            port="5432"
        )
        print("Database connection initialized")
    except DatabaseError as e:
        print(f"Database connection error: {str(e)}")
    
    yield  # App is running
    
    # Shutdown: Close database connections
    Database.close_all_connections()
    print("Database connections closed")

# Initialize FastAPI app with lifespan
app = FastAPI(title="BGG Flashcards API", lifespan=lifespan)

# Configure CORS for the API
origins = ["*"]  # Replace with specific origins in production

@app.middleware("http")
async def cors_middleware(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# Authentication endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User endpoints
@app.post("/users/", response_model=User)
async def create_user(user: UserCreate):
    with CursorFromConnectionPool() as cursor:
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Hash the password and create the user
        hashed_password = get_password_hash(user.password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (user.username, user.email, hashed_password)
        )
        user_id = cursor.fetchone()[0]
        
        return User(id=user_id, username=user.username, email=user.email)

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Game endpoints
@app.get("/games/{game_id}", response_model=Game)
async def get_game(game_id: int, _: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        cursor.execute(
            "SELECT id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished FROM games WHERE id = %s",
            (game_id,)
        )
        game_data = cursor.fetchone()
        if not game_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )
        
        selevted_id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished = game_data
        return Game(
            id=selevted_id,
            name=name,
            avg_rating=avg_rating,
            min_players=min_players,
            max_players=max_players,
            image_path=image_path,
            is_expansion=is_expansion,
            yearpublished=yearpublished
        )

@app.post("/games/search", response_model=GameSearchResults)
async def search_games(search: GameSearch, _: User = Depends(get_current_user)):
    results = {"local_games": [], "local_expansions": [], "bgg_games": []}
    
    # Search in local database
    with CursorFromConnectionPool() as cursor:
        # Check if search query is a numeric ID
        is_id_search = search.query.isdigit()
        
        if is_id_search:
            cursor.execute(
                "SELECT id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished FROM games WHERE id = %s",
                (search.query,)
            )
        else:
            # Rank results by relevance
            cursor.execute(
                """
                SELECT id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished,
                       CASE 
                           WHEN LOWER(name) = LOWER(%s) THEN 1 
                           WHEN LOWER(name) LIKE LOWER(%s) THEN 2 
                           ELSE 3 
                       END AS match_rank 
                FROM games 
                WHERE name ILIKE %s
                ORDER BY match_rank, avg_rating DESC NULLS LAST, name
                """,
                (search.query, f'{search.query}%', f'%{search.query}%')
            )
            
        for game_data in cursor.fetchall():
            # Handle ID search vs name search with match_rank
            if is_id_search or len(game_data) == 8:
                selected_id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished = game_data
            else:
                selected_id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished, _ = game_data
            
            game = Game(
                id=selected_id,
                name=name,
                avg_rating=avg_rating,
                min_players=min_players,
                max_players=max_players,
                image_path=image_path,
                is_expansion=is_expansion,
                yearpublished=yearpublished
            )
            
            # Sort games into appropriate list
            if is_expansion == 1:
                results["local_expansions"].append(game)
            else:
                results["local_games"].append(game)
    
    # Search BoardGameGeek API will be handled by a separate endpoint
    # to avoid duplicate searches and improve performance
    
    return results

@app.post("/games/search_bgg", response_model=list[Game])
async def search_bgg(search: GameSearch, _: User = Depends(get_current_user)):
    from models.game import Game as GameModel
    
    # Call the existing BGG search function
    bgg_games = GameModel.search_bgg_api(search.query)
    
    # Convert to Pydantic model
    results = []
    for game in bgg_games:
        results.append(Game(
            id=game.id,
            name=game.name,
            avg_rating=game.avg_rating,
            min_players=game.min_players,
            max_players=game.max_players,
            image_path=game.image_path,
            is_expansion=game.is_expansion,
            yearpublished=game.yearpublished
        ))
    
    return results

@app.get("/users/me/games", response_model=list[Game])
async def get_user_games(current_user: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        cursor.execute(
            """
            SELECT g.id, g.name, g.avg_rating, g.min_players, g.max_players, g.image_path, g.is_expansion, g.yearpublished
            FROM games g
            JOIN user_saved_games usg ON g.id = usg.game_id
            WHERE usg.user_id = %s
            """,
            (current_user.id,)
        )
        
        games = []
        for game_data in cursor.fetchall():
            selected_id, name, avg_rating, min_players, max_players, image_path, is_expansion, yearpublished = game_data
            games.append(Game(
                id=selected_id,
                name=name,
                avg_rating=avg_rating,
                min_players=min_players,
                max_players=max_players,
                image_path=image_path,
                is_expansion=is_expansion,
                yearpublished=yearpublished
            ))
        
        return games

@app.post("/users/me/games")
async def save_game(game_op: UserGameOperation, current_user: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        # Check if game exists
        cursor.execute("SELECT id FROM games WHERE id = %s", (game_op.game_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )
        
        # Save game to user's collection
        cursor.execute(
            "INSERT INTO user_saved_games (user_id, game_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (current_user.id, game_op.game_id)
        )
        
        return {"status": "success"}

@app.delete("/users/me/games/{game_id}")
async def remove_game(game_id: int, current_user: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        cursor.execute(
            "DELETE FROM user_saved_games WHERE user_id = %s AND game_id = %s",
            (current_user.id, game_id)
        )
        
        return {"status": "success"}

# Flashcard endpoints
@app.get("/games/{game_id}/flashcards", response_model=list[Flashcard])
async def get_game_flashcards(game_id: int, _: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        cursor.execute(
            """
            SELECT id, game_id, user_id, category, title, content
            FROM flashcards
            WHERE game_id = %s
            ORDER BY category, created_at
            """,
            (game_id,)
        )
        
        flashcards = []
        for flashcard_data in cursor.fetchall():
            selected_id, game_id, user_id, category, title, content = flashcard_data
            flashcards.append(Flashcard(
                id=selected_id,
                game_id=game_id,
                user_id=user_id,
                category=category,
                title=title,
                content=content
            ))
        
        return flashcards

@app.post("/flashcards", response_model=Flashcard)
async def create_flashcard(flashcard: FlashcardCreate, current_user: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        # Check if game exists
        cursor.execute("SELECT id FROM games WHERE id = %s", (flashcard.game_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )
        
        # Create the flashcard
        cursor.execute(
            """
            INSERT INTO flashcards (game_id, user_id, category, title, content)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (flashcard.game_id, current_user.id, flashcard.category, flashcard.title, flashcard.content)
        )
        flashcard_id = cursor.fetchone()[0]
        
        return Flashcard(
            id=flashcard_id,
            game_id=flashcard.game_id,
            user_id=current_user.id,
            category=flashcard.category,
            title=flashcard.title,
            content=flashcard.content
        )

@app.get("/flashcards/{flashcard_id}", response_model=Flashcard)
async def get_flashcard(flashcard_id: int, _: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        cursor.execute(
            "SELECT game_id, user_id, category, title, content FROM flashcards WHERE id = %s",
            (flashcard_id,)
        )
        flashcard_data = cursor.fetchone()
        if not flashcard_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flashcard not found"
            )
        
        game_id, user_id, category, title, content = flashcard_data
        
        return Flashcard(
            id=flashcard_id,
            game_id=game_id,
            user_id=user_id,
            category=category,
            title=title,
            content=content
        )

@app.put("/flashcards/{flashcard_id}", response_model=Flashcard)
async def update_flashcard(
    flashcard_id: int,
    flashcard: FlashcardCreate,
    current_user: User = Depends(get_current_user)
):
    with CursorFromConnectionPool() as cursor:
        # Check if flashcard exists and belongs to the user
        cursor.execute(
            "SELECT user_id FROM flashcards WHERE id = %s",
            (flashcard_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flashcard not found"
            )
        
        user_id = result[0]
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own flashcards"
            )
        
        # Update the flashcard
        cursor.execute(
            """
            UPDATE flashcards
            SET category = %s, title = %s, content = %s
            WHERE id = %s
            """,
            (flashcard.category, flashcard.title, flashcard.content, flashcard_id)
        )
        
        return Flashcard(
            id=flashcard_id,
            game_id=flashcard.game_id,
            user_id=current_user.id,
            category=flashcard.category,
            title=flashcard.title,
            content=flashcard.content
        )

@app.delete("/flashcards/{flashcard_id}")
async def delete_flashcard(flashcard_id: int, current_user: User = Depends(get_current_user)):
    with CursorFromConnectionPool() as cursor:
        # Check if flashcard exists and belongs to the user
        cursor.execute(
            "SELECT user_id FROM flashcards WHERE id = %s",
            (flashcard_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flashcard not found"
            )
        
        user_id = result[0]
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own flashcards"
            )
        
        # Delete the flashcard
        cursor.execute("DELETE FROM flashcards WHERE id = %s", (flashcard_id,))
        
        return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)