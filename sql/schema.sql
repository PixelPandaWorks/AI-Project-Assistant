-- ============================================
-- AI Project Assistant — Database Schema
-- Run this SQL in the Supabase SQL Editor
-- ============================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. Projects
-- ============================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. Project Briefs (1:1 with projects)
-- ============================================
CREATE TABLE project_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    goals JSONB DEFAULT '[]'::jsonb,
    reference_links JSONB DEFAULT '[]'::jsonb,
    target_audience TEXT,
    tech_stack TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 3. Conversations (chat history)
-- ============================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 4. Images (generated + analyzed)
-- ============================================
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    url TEXT NOT NULL,
    analysis TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. Project Memory (persistent knowledge)
-- ============================================
CREATE TABLE project_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    memory_key TEXT NOT NULL,
    memory_value JSONB NOT NULL,
    source TEXT DEFAULT 'user' CHECK (source IN ('user', 'assistant', 'agent')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Composite unique: one key per project per source
CREATE UNIQUE INDEX idx_memory_project_key ON project_memory(project_id, memory_key);

-- ============================================
-- 6. Agent Executions (background job tracking)
-- ============================================
CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    task_type TEXT DEFAULT 'organize_knowledge',
    result JSONB,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- Indexes for fast lookups
-- ============================================
CREATE INDEX idx_conversations_project ON conversations(project_id, created_at);
CREATE INDEX idx_images_project ON images(project_id);
CREATE INDEX idx_memory_project ON project_memory(project_id);
CREATE INDEX idx_agent_exec_project ON agent_executions(project_id);
CREATE INDEX idx_agent_exec_status ON agent_executions(status);
