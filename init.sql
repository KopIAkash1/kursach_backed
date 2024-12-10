-- Подключение к базе данных SCHEDULE_BASE
\connect main_data_db;

-- Создание таблицы USER
CREATE TABLE "USER" (
    user_id SERIAL PRIMARY KEY,         -- Уникальный идентификатор пользователя (автоинкремент)
    username VARCHAR(255) NOT NULL,         -- Имя пользователя
    password VARCHAR(255) NOT NULL,
    path_to_file TEXT                          -- URL или путь к изображению пользователя
);

-- Создание таблицы SCHEDULE
CREATE TABLE "SCHEDULE" (
    schedule_id SERIAL PRIMARY KEY,     -- Уникальный идентификатор расписания (автоинкремент)
    file_path_to_schedule TEXT NOT NULL -- Путь к файлу расписания
);

-- Создание таблицы USER_LIST
CREATE TABLE "USER_LIST" (
    user_user_id INT NOT NULL,          -- Внешний ключ на USER (user_id)
    schedule_id INT NOT NULL,           -- Внешний ключ на SCHEDULE (schedule_id)
    PRIMARY KEY (user_user_id, schedule_id), -- Композитный первичный ключ
    FOREIGN KEY (user_user_id) REFERENCES "USER" (user_id) ON DELETE CASCADE,
    FOREIGN KEY (schedule_id) REFERENCES "SCHEDULE" (schedule_id) ON DELETE CASCADE
);
