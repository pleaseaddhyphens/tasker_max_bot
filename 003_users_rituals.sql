-- Миграция для добавления пользователей и ритуалов
-- Запустить: psql -U tasker_user -d tasker -f 003_users_rituals.sql

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
  id                    BIGSERIAL PRIMARY KEY,
  max_user_id           BIGINT UNIQUE NOT NULL,       -- ID пользователя в MAX
  first_name            VARCHAR(255),                 -- Имя
  last_name             VARCHAR(255),                 -- Фамилия
  username              VARCHAR(255),                 -- Username
  morning_ritual_time   TIME,                         -- Время утреннего ритуала (HH:MM)
  evening_ritual_time   TIME,                         -- Время вечернего ритуала (HH:MM)
  timezone              VARCHAR(50) DEFAULT 'UTC',    -- Часовой пояс
  onboarding_step       VARCHAR(50) DEFAULT 'none',   -- Шаг онбординга (none, morning_time, evening_time, completed)
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Таблица логов самочувствия
CREATE TABLE IF NOT EXISTS mood_logs (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(max_user_id) ON DELETE CASCADE,
  mood_level      INT NOT NULL CHECK (mood_level >= 1 AND mood_level <= 7),  -- 1-7
  ritual_type     VARCHAR(20) NOT NULL,  -- 'morning' или 'evening'
  notes           TEXT,                  -- Опциональные заметки
  logged_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_users_max_user_id ON users(max_user_id);
CREATE INDEX IF NOT EXISTS idx_mood_logs_user_id ON mood_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_logs_logged_at ON mood_logs(logged_at);

-- Комментарии
COMMENT ON TABLE users IS 'Пользователи бота с настройками ритуалов';
COMMENT ON TABLE mood_logs IS 'История записей самочувствия пользователей';

COMMENT ON COLUMN mood_logs.mood_level IS '1=Апатия, 2=Пассивность, 3=Расслабленность, 4=Баланс, 5=Включенность, 6=Перевозбужденность, 7=Паника';

