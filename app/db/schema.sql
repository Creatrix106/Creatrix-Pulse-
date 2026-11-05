-- Creatrix Pulse Production PostgreSQL 15+ Schema
-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Datasets Table
CREATE TABLE IF NOT EXISTS datasets (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    row_count INTEGER NOT NULL DEFAULT 0,
    column_count INTEGER NOT NULL DEFAULT 0,
    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    columns JSONB NOT NULL DEFAULT '[]'::jsonb,
    date_range JSONB DEFAULT NULL,
    filter_options JSONB NOT NULL DEFAULT '{"categories": [], "regions": []}'::jsonb,
    error_message TEXT DEFAULT NULL,
    schema_metadata JSONB DEFAULT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at BIGINT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_datasets_user_id ON datasets(user_id);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);

-- Dataset Rows (Normalized / Columnar Cache)
CREATE TABLE IF NOT EXISTS dataset_rows (
    id VARCHAR(64) PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    order_id VARCHAR(128),
    transaction_date DATE NOT NULL,
    product_id VARCHAR(128),
    product_name VARCHAR(255) NOT NULL,
    product_category VARCHAR(128),
    region VARCHAR(128),
    customer_identifier VARCHAR(128),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    revenue DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cost DOUBLE PRECISION DEFAULT NULL,
    raw_payload JSONB DEFAULT NULL
);

-- Rapid Query Indexes: B-Tree on (dataset_id, transaction_date)
CREATE INDEX IF NOT EXISTS idx_dataset_rows_dataset_date ON dataset_rows(dataset_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_dataset_rows_category ON dataset_rows(dataset_id, product_category);
CREATE INDEX IF NOT EXISTS idx_dataset_rows_region ON dataset_rows(dataset_id, region);
CREATE INDEX IF NOT EXISTS idx_dataset_rows_customer ON dataset_rows(dataset_id, customer_identifier);
CREATE INDEX IF NOT EXISTS idx_dataset_rows_product ON dataset_rows(dataset_id, product_id);

-- Dataset Column Mappings
CREATE TABLE IF NOT EXISTS dataset_mappings (
    id VARCHAR(64) PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    source_column VARCHAR(255) NOT NULL,
    target_dimension VARCHAR(128) NOT NULL,
    data_type VARCHAR(64) NOT NULL DEFAULT 'string'
);

CREATE INDEX IF NOT EXISTS idx_dataset_mappings_ds ON dataset_mappings(dataset_id);

-- Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(64) PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    format VARCHAR(50) NOT NULL DEFAULT 'csv',
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    row_count INTEGER NOT NULL DEFAULT 0,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    file_path TEXT DEFAULT NULL,
    content TEXT DEFAULT NULL,
    download_url TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_dataset_id ON reports(dataset_id);
