-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Games table
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    avg_rating DECIMAL(3,1),
    min_players INTEGER,
    max_players INTEGER,
    image_path VARCHAR(255),
    yearpublished INTEGER,
    is_expansion BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Image storage using PostgreSQL Large Objects
    image_oid OID,
    image_mimetype VARCHAR(50),
    image_size INTEGER
);

-- Comments for image storage columns
COMMENT ON COLUMN games.image_oid IS 'OID reference to Large Object containing image data';
COMMENT ON COLUMN games.image_mimetype IS 'MIME type of the image (e.g., image/jpeg, image/png)';
COMMENT ON COLUMN games.image_size IS 'Size of the image in bytes';

-- User saved games (many-to-many relationship)
CREATE TABLE user_saved_games (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, game_id)
);

-- Flashcards table
CREATE TABLE flashcards (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL CHECK (category IN ('Setup', 'Rules', 'Events', 'Points', 'End of the game', 'Notes')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Privacy control for flashcards
    is_private BOOLEAN DEFAULT FALSE
);

-- Comment for privacy column
COMMENT ON COLUMN flashcards.is_private IS 'Whether this flashcard is private to the creator (TRUE) or visible to all users (FALSE)';

-- Indexes for performance optimization
-- Index for games with images (sparse index)
CREATE INDEX idx_games_has_image_oid ON games (image_oid) WHERE image_oid IS NOT NULL;

-- Index for flashcard privacy filtering
CREATE INDEX idx_flashcards_privacy ON flashcards (is_private, user_id);

-- Index for flashcards by game (common query pattern)
CREATE INDEX idx_flashcards_game_id ON flashcards (game_id);

-- Index for user saved games lookup
CREATE INDEX idx_user_saved_games_user_id ON user_saved_games (user_id);