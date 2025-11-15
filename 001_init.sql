-- Полная инициализация БД для Tasker MAX Bot
-- Выполняется автоматически при первом запуске PostgreSQL контейнера

-- ========== Чаты ==========
CREATE TABLE IF NOT EXISTS chats (
  id              BIGSERIAL PRIMARY KEY,
  max_chat_id     TEXT UNIQUE NOT NULL,          -- ID чата в MAX мессенджере
  name            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========== Задачи ==========
CREATE TABLE IF NOT EXISTS tasks (
  id           BIGSERIAL PRIMARY KEY,
  chat_id      BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
  creator_id   BIGINT NOT NULL,                   -- Кто создал задачу
  assignee_id  BIGINT,                            -- Исполнитель задачи (может быть NULL)
  title        VARCHAR(500) NOT NULL,
  description  TEXT,                              -- Описание задачи
  tag          VARCHAR(100),                      -- Тег/категория задачи
  status       VARCHAR(20) DEFAULT 'active',      -- active, completed, archived
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  deadline     TIMESTAMPTZ,                       -- Срок выполнения
  completed_at TIMESTAMPTZ,                       -- Дата выполнения
  reminder_at  TIMESTAMPTZ                        -- Дата напоминания
);

-- ========== Пользователи ==========
CREATE TABLE IF NOT EXISTS users (
  id                    BIGSERIAL PRIMARY KEY,
  max_user_id           BIGINT UNIQUE NOT NULL,        -- ID пользователя в MAX
  first_name            VARCHAR(255),                  -- Имя
  last_name             VARCHAR(255),                  -- Фамилия
  username              VARCHAR(255),                  -- Username
  morning_ritual_time   TIME,                          -- Время утреннего ритуала (HH:MM)
  evening_ritual_time   TIME,                          -- Время вечернего ритуала (HH:MM)
  timezone              VARCHAR(50) DEFAULT 'UTC',     -- Часовой пояс
  onboarding_step       VARCHAR(50) DEFAULT 'none',    -- Шаг онбординга
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- ========== Логи самочувствия ==========
CREATE TABLE IF NOT EXISTS mood_logs (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(max_user_id) ON DELETE CASCADE,
  mood_level      INT NOT NULL CHECK (mood_level >= 1 AND mood_level <= 7),
  ritual_type     VARCHAR(20) NOT NULL,            -- 'morning' или 'evening'
  notes           TEXT,                            -- Опциональные заметки
  logged_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ========== Индексы для производительности ==========
CREATE INDEX IF NOT EXISTS idx_chats_max_chat_id ON chats(max_chat_id);
CREATE INDEX IF NOT EXISTS idx_tasks_chat_id ON tasks(chat_id);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_reminder ON tasks(reminder_at);
CREATE INDEX IF NOT EXISTS idx_users_max_user_id ON users(max_user_id);
CREATE INDEX IF NOT EXISTS idx_mood_logs_user_id ON mood_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_logs_logged_at ON mood_logs(logged_at);

-- ========== Комментарии ==========
COMMENT ON TABLE chats IS 'Чаты в MAX мессенджере';
COMMENT ON TABLE tasks IS 'Задачи, создаваемые и управляемые в чатах';
COMMENT ON TABLE users IS 'Пользователи бота с настройками ритуалов';
COMMENT ON TABLE mood_logs IS 'История записей самочувствия пользователей';
COMMENT ON COLUMN mood_logs.mood_level IS '1=Апатия, 2=Пассивность, 3=Расслабленность, 4=Баланс, 5=Включенность, 6=Перевозбужденность, 7=Паника';

