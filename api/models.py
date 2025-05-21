# This file is deprecated and has been moved to schemas.py
# Keeping this file for backward compatibility but it should not be used directly
# Import from api.schemas instead

from api.schemas import (
    BaseModel, Field, Optional, List,
    UserBase, UserCreate, UserLogin, User, TokenData, Token,
    GameBase, Game, GameSearch, UserGameOperation,
    FlashcardBase, FlashcardCreate, Flashcard, GameSearchResults
)