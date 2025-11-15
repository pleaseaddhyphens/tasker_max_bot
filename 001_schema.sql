-- Schema initialization for tasker_max_bot
-- This file is executed automatically by the official Postgres image
-- when mounted to /docker-entrypoint-initdb.d

-- Chats (team/group) within the messenger
CREATE TABLE IF NOT EXISTS chats (
  id              BIGSERIAL PRIMARY KEY,
  max_chat_id     TEXT UNIQUE NOT NULL,          -- messenger chat id
  name            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tasks created and managed in chats
CREATE TABLE IF NOT EXISTS tasks (
  id           BIGSERIAL PRIMARY KEY,
  chat_id      BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
  creator_id   BIGINT NOT NULL,       -- Кто создал задачу
  assignee_id  BIGINT,                -- Исполнитель задачи (может быть NULL)
  title        VARCHAR(500) NOT NULL,
  description  TEXT,                  -- Описание задачи
  tag          VARCHAR(100),          -- Тег/категория задачи
  status       VARCHAR(20) DEFAULT 'active', -- active, completed, archived
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  deadline     TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,           -- Дата выполнения
  reminder_at  TIMESTAMPTZ            -- Дата напоминания
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_chat_id ON tasks(chat_id);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_reminder ON tasks(reminder_at);
