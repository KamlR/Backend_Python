CREATE TABLE IF NOT EXISTS public.users (
    seller_id BIGSERIAL PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    is_verified_seller BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.items (
    item_id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT,
    name TEXT,
    description TEXT,
    category INTEGER,
    images_qty INTEGER DEFAULT 0
);