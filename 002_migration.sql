-- Migration script to update existing database schema
-- Run this if you already have data in the old schema

-- Add new columns to tasks table
ALTER TABLE tasks 
  ADD COLUMN IF NOT EXISTS assignee_id BIGINT,
  ADD COLUMN IF NOT EXISTS tag VARCHAR(100),
  ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS reminder_at TIMESTAMPTZ;

-- Update existing records to have 'active' status
UPDATE tasks SET status = 'active' WHERE status IS NULL;

-- Create new indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_reminder ON tasks(reminder_at);

-- Verify migration
SELECT 
  column_name, 
  data_type, 
  is_nullable
FROM information_schema.columns 
WHERE table_name = 'tasks'
ORDER BY ordinal_position;

ANALYZE tasks;
