from pydantic import BaseModel, Field
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class TokenData(BaseModel):
    username: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class GameBase(BaseModel):
    name: str
    avg_rating: Optional[float] = None
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    image_path: Optional[str] = None
    is_expansion: Optional[int] = Field(default=0)
    yearpublished: Optional[int] = None


class Game(GameBase):
    id: int

    class Config:
        orm_mode = True


class GameSearch(BaseModel):
    query: str


class UserGameOperation(BaseModel):
    game_id: int


class FlashcardBase(BaseModel):
    game_id: int
    category: str
    title: str
    content: str


class FlashcardCreate(FlashcardBase):
    pass


class Flashcard(FlashcardBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True


class GameSearchResults(BaseModel):
    local_games: List[Game]
    local_expansions: List[Game]
    bgg_games: List[Game]