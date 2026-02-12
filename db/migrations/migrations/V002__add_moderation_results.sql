CREATE TABLE IF NOT EXISTS public.moderation_results (
    task_id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES public.items (item_id),
    status VARCHAR(20) NOT NULL CHECK (
        status IN (
            'pending',
            'completed',
            'failed'
        )
    ),
    is_violation BOOLEAN DEFAULT NULL,
    probability FLOAT,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    processed_at TIMESTAMP DEFAULT NULL
);