-- ============================================================================
-- UNIVERSITY FINAL YEAR PROJECT MANAGEMENT SYSTEM - SIMPLIFIED SCHEMA
-- ============================================================================
-- Simplified: Merged users into one table, direct links, no redundant FKs.
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector; -- For vector embeddings (SBERT)
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For trigram similarity (alternative to embeddings)

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================

-- Users: Unified table for students, mentors, admins
CREATE TABLE users (
    id SERIAL PRIMARY KEY, -- Auto-incrementing ID for all users
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(150),
    middle_name VARCHAR(150),  -- Added for three-name structure
    last_name VARCHAR(150),
    role VARCHAR(50) NOT NULL,  -- 'student', 'mentor', 'coordinator' (manages mentors; coordinators can also mentor students)
    registration_number VARCHAR(50) UNIQUE,  -- Only required for students
    mentor_id INT REFERENCES users(id) ON DELETE SET NULL,  -- Mentor for students (can be mentor or coordinator)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projects: FYP submissions
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    main_objective TEXT,
    specific_objectives JSONB DEFAULT '[]',
    project_description TEXT,
    implementation_details TEXT, 
    year INT NOT NULL,
    status VARCHAR(50) DEFAULT 'proposed',  -- Possible statuses: 'proposed', 'approved', 'rejected', 'completed'
    user_id INT REFERENCES users(id) ON DELETE CASCADE,  -- Creator

    -- Embeddings for duplicate detection (768-dim vectors for SBERT)
    title_embedding vector(768), 
    objectives_embedding vector(768), 
    combined_embedding vector(768), -- SBERT embedding for title + objectives

    -- Duplicate detection metadata
    last_similarity_check TIMESTAMP,
    is_flagged_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_check_score FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project_Users: Links users to projects (supports group projects)
CREATE TABLE project_users (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'lead',  -- 'lead' or 'member'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id) -- Prevent duplicate entries for the same user and project
);



-- Duplicate Flags
CREATE TABLE duplicate_flags (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    similar_project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    similarity_score FLOAT NOT NULL,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by INT REFERENCES users(id) ON DELETE SET NULL, -- mentor or coordinator who reviewed the flag
    reviewed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- FTS indexes
CREATE INDEX idx_projects_title_fts ON projects USING GIN(to_tsvector('english', title));
CREATE INDEX idx_projects_objectives_fts ON projects USING GIN(to_tsvector('english', main_objective));

-- Vector indexes
CREATE INDEX idx_projects_title_embedding ON projects USING ivfflat(title_embedding vector_cosine_ops) WITH (lists=100);
CREATE INDEX idx_projects_objectives_embedding ON projects USING ivfflat(objectives_embedding vector_cosine_ops) WITH (lists=100);
CREATE INDEX idx_projects_combined_embedding ON projects USING ivfflat(combined_embedding vector_cosine_ops) WITH (lists=100);

-- Other indexes
CREATE INDEX idx_projects_year_status ON projects(year, status);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_project_users_project_id ON project_users(project_id);
-- ============================================================================
-- SAMPLE ADMIN SETTINGS (populate as needed)
-- ============================================================================

INSERT INTO admin_settings (setting_key, setting_value, description) VALUES
    ('DUPLICATE_SEARCH_YEARS_BACK', '3', 'How many years back to search for duplicates'),
    ('DUPLICATE_SIMILARITY_THRESHOLD', '0.6', 'Threshold score (0-1) to flag for admin review'),
    ('DUPLICATE_AUTO_FLAG_THRESHOLD', '0.8', 'Threshold score to auto-flag as duplicate'),
    ('DUPLICATE_ALGORITHM', 'HYBRID', 'Algorithm: TFIDF, EMBEDDING, or HYBRID'),
    ('MENTOR_MAX_LOAD_DEFAULT', '10', 'Default max students per mentor'),
    ('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2', 'SBERT model for embeddings')
ON CONFLICT (setting_key) DO NOTHING;

-- ============================================================================
-- TRIGGERS FOR DATA INTEGRITY & AUTOMATION
-- ============================================================================

-- Trigger: Update project.updated_at on changes
CREATE OR REPLACE FUNCTION update_project_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_project_timestamp
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION update_project_timestamp();

-- Trigger: Prevent overlapping appointments for the same mentor
-- (Removed with appointments feature)

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
