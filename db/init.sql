-- =====================================================
-- База данных проекта «Учет домашних животных»
-- Вариант 31: расчет нормы кормления по весу и возрасту,
-- медкарта и карточка питомца
-- =====================================================

-- Карточка питомца
CREATE TABLE IF NOT EXISTS pets (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,   -- имена питомцев не повторяются
    species     VARCHAR(20)  NOT NULL CHECK (species IN ('dog', 'cat')),
    breed       VARCHAR(100),
    sex         VARCHAR(10),
    weight_kg   NUMERIC(5,2) NOT NULL CHECK (weight_kg > 0),
    age_years   NUMERIC(4,1) NOT NULL CHECK (age_years >= 0),
    birth_date  DATE,
    owner_name  VARCHAR(100),
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Медкарта: записи о визитах и здоровье питомца
CREATE TABLE IF NOT EXISTS medcard (
    id           SERIAL PRIMARY KEY,
    pet_id       INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    visit_date   DATE NOT NULL,
    diagnosis    VARCHAR(200),
    temperature_c NUMERIC(3,1),
    weight_kg    NUMERIC(5,2),
    notes        TEXT
);

-- Журнал расчетов нормы кормления
CREATE TABLE IF NOT EXISTS feeding_history (
    id            SERIAL PRIMARY KEY,
    pet_id        INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    weight_kg     NUMERIC(5,2) NOT NULL,
    age_years     NUMERIC(4,1) NOT NULL,
    daily_kcal    NUMERIC(7,1) NOT NULL,
    daily_food_g  NUMERIC(7,1) NOT NULL,
    meals_per_day INTEGER NOT NULL,
    advice        TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------- Первичные данные ----------------
INSERT INTO pets (name, species, breed, sex, weight_kg, age_years, birth_date, owner_name) VALUES
    ('Барсик',  'dog', 'Лабрадор ретривер', 'male',   28.50, 3.0, '2023-04-12', 'Иванова Анна'),
    ('Мурка',   'cat', 'Британская короткошёрстная', 'female', 4.20, 2.0, '2024-01-25', 'Иванова Анна'),
    ('Ричи',   'dog', 'Джек-рассел-терьер', 'male',    7.80, 0.5, '2025-05-10', 'Иванова Анна'),
    ('Персик',  'cat', 'Мейн-кун', 'male',             7.10, 6.0, '2020-03-03', 'Иванова Анна');

INSERT INTO medcard (pet_id, visit_date, diagnosis, temperature_c, weight_kg, notes) VALUES
    (1, '2026-02-14', 'Плановый осмотр',           38.6, 28.50, 'Здоров, прививки актуальны'),
    (1, '2025-09-02', 'Аллергический дерматит',    38.9, 27.80, 'Назначена гипоаллергенная диета'),
    (2, '2026-03-01', 'Плановый осмотр',           38.4,  4.20, 'Здорова, вес в норме'),
    (3, '2026-06-20', 'Вывих лапы (маленькая)',    38.7,  7.90, 'Наложена повязка, ограничить нагрузку'),
    (4, '2026-01-18', 'УЗИ брюшной полости',       38.5,  7.10, 'Патологий не обнаружено');

INSERT INTO feeding_history (pet_id, weight_kg, age_years, daily_kcal, daily_food_g, meals_per_day, advice) VALUES
    (1, 28.50, 3.0, 1442.0, 390.0, 2, 'Разделите дневную норму на 2 приема пищи'),
    (2,  4.20, 2.0,  220.0,  59.0, 3, 'Кормите 3 раза в день небольшими порциями');
