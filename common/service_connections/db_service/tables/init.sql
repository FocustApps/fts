-- Initialize Fenrir Database Tables
-- This script creates all required tables
-- Note: Database creation should be handled by Docker environment variables
-- Set POSTGRES_DB=fenrir in your docker-compose.yml or Dockerfile

-- Create all tables directly in this file for Docker compatibility

-- Create identifier table
CREATE TABLE IF NOT EXISTS identifier (
    id SERIAL PRIMARY KEY,
    page_id INTEGER NOT NULL,
    element_name VARCHAR(96) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locator_strategy VARCHAR(96) NOT NULL,
    locator_query VARCHAR(96) NOT NULL,
    environments JSONB DEFAULT '[]'::jsonb
);

-- Create user table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(96) UNIQUE NOT NULL,
    email VARCHAR(96) NOT NULL,
    password VARCHAR(96),
    secret_provider VARCHAR(96),
    secret_url VARCHAR(1024),
    secret_name VARCHAR(1024),
    environment_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NULL
);

-- Create environment table
CREATE TABLE IF NOT EXISTS environment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(96) UNIQUE NOT NULL,
    environment_designation VARCHAR(80) NOT NULL,
    url VARCHAR(512) NOT NULL,
    api_url VARCHAR(512) DEFAULT NULL,
    status VARCHAR(96) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NULL,
    users JSONB DEFAULT '[]'::jsonb
);

-- Create page table
CREATE TABLE IF NOT EXISTS page (
    id SERIAL PRIMARY KEY,
    environments JSONB NOT NULL,
    page_name VARCHAR(96) UNIQUE NOT NULL,
    page_url VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    identifiers JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Create email processor table
CREATE TABLE IF NOT EXISTS "emailProcessorTable" (
    id SERIAL PRIMARY KEY,
    email_item_id INTEGER UNIQUE NOT NULL,
    multi_item_email_ids JSONB DEFAULT NULL,
    multi_email_flag BOOLEAN DEFAULT FALSE,
    multi_attachment_flag BOOLEAN DEFAULT FALSE,
    system VARCHAR(96) DEFAULT NULL,          -- NEW: maps to WorkItemTable.system (SystemEnum)
    test_name VARCHAR(255) DEFAULT NULL,
    requires_processing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NULL,
    last_processed_at TIMESTAMP DEFAULT NULL
);


-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_identifier_page_id ON identifier(page_id);
CREATE INDEX IF NOT EXISTS idx_identifier_element_name ON identifier(element_name);
CREATE INDEX IF NOT EXISTS idx_identifier_locator_strategy ON identifier(locator_strategy);

CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);
CREATE INDEX IF NOT EXISTS idx_user_environment_id ON "user"(environment_id);

CREATE INDEX IF NOT EXISTS idx_environment_name ON environment(name);
CREATE INDEX IF NOT EXISTS idx_environment_designation ON environment(environment_designation);
CREATE INDEX IF NOT EXISTS idx_environment_status ON environment(status);

CREATE INDEX IF NOT EXISTS idx_page_page_name ON page(page_name);
CREATE INDEX IF NOT EXISTS idx_page_environments ON page USING GIN(environments);
CREATE INDEX IF NOT EXISTS idx_page_identifiers ON page USING GIN(identifiers);

CREATE INDEX IF NOT EXISTS idx_email_item_email_item_id ON "emailProcessorTable"(email_item_id);
CREATE INDEX IF NOT EXISTS idx_email_item_requires_processing ON "emailProcessorTable"(requires_processing);
CREATE INDEX IF NOT EXISTS idx_email_item_created_at ON "emailProcessorTable"(created_at);
CREATE INDEX IF NOT EXISTS idx_email_item_system ON "emailProcessorTable"(system);
CREATE INDEX IF NOT EXISTS idx_email_item_last_processed_at ON "emailProcessorTable"(last_processed_at);

-- Add any foreign key constraints after all tables are created
-- Note: Based on the model analysis, these appear to be the main relationships:
-- identifier.page_id should reference page.id
-- user.environment_id should reference environment.id

ALTER TABLE identifier 
ADD CONSTRAINT fk_identifier_page_id 
FOREIGN KEY (page_id) REFERENCES page(id) ON DELETE CASCADE;

ALTER TABLE "user" 
ADD CONSTRAINT fk_user_environment_id 
FOREIGN KEY (environment_id) REFERENCES environment(id) ON DELETE CASCADE;