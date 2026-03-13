CREATE TABLE IF NOT EXISTS public.account (
    id SERIAL PRIMARY KEY,
    login TEXT,
    password TEXT,
    is_blocked BOOLEAN DEFAULT FALSE
);