-- SQL for creating a table to store drafted emails
CREATE TABLE IF NOT EXISTS drafted_emails (
    id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT,
    email_draft TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
