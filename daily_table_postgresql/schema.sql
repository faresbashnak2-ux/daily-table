CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS menu (
    id BIGSERIAL PRIMARY KEY,
    menu_date DATE NOT NULL UNIQUE,
    main_dish TEXT NOT NULL,
    side_dish TEXT,
    salad TEXT,
    dessert TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS ratings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    menu_date DATE NOT NULL,
    food_choice SMALLINT NOT NULL CHECK (food_choice BETWEEN 1 AND 5),
    taste SMALLINT NOT NULL CHECK (taste BETWEEN 1 AND 5),
    cleanliness SMALLINT NOT NULL CHECK (cleanliness BETWEEN 1 AND 5),
    service SMALLINT NOT NULL CHECK (service BETWEEN 1 AND 5),
    comment VARCHAR(500),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, menu_date)
);

CREATE INDEX IF NOT EXISTS ratings_menu_date_idx ON ratings(menu_date);
