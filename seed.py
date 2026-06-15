# seed.py - Скрипт для создания таблиц и заполнения БД нормативными данными
import asyncio
from sqlalchemy import text
from database import engine


async def seed_data():
    async with engine.begin() as conn:
        print("1. Удаление старых таблиц (сброс структуры)...")
        # CASCADE удалит таблицы даже если между ними есть связи
        await conn.execute(text("DROP TABLE IF EXISTS climatology, materials, window_types CASCADE;"))

        print("2. Создание таблиц с актуальной структурой...")
        await conn.execute(text("""
            CREATE TABLE climatology (
                id SERIAL PRIMARY KEY,
                city_name VARCHAR(100) NOT NULL UNIQUE,
                t_winter_5day NUMERIC(4, 1) NOT NULL,
                t_heating_avg NUMERIC(4, 1) NOT NULL,
                heating_duration INTEGER NOT NULL,
                t_summer_max NUMERIC(4, 1) NOT NULL
            );
        """))

        await conn.execute(text("""
            CREATE TABLE materials (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL UNIQUE,
                density NUMERIC(6, 1) NOT NULL,
                thermal_conductivity NUMERIC(5, 3) NOT NULL
            );
        """))

        await conn.execute(text("""
            CREATE TABLE window_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL UNIQUE,
                r_value NUMERIC(4, 2) NOT NULL,
                solar_factor NUMERIC(3, 2) NOT NULL
            );
        """))

        print("3. Наполнение таблицы 'Климатология'...")
        await conn.execute(text("""
            INSERT INTO climatology (city_name, t_winter_5day, t_heating_avg, heating_duration, t_summer_max) VALUES
            ('Москва', -25.0, -2.2, 205, 28.0),
            ('Санкт-Петербург', -24.0, -1.8, 213, 26.0),
            ('Краснодар', -14.0, 2.0, 149, 34.0),
            ('Новосибирск', -37.0, -5.8, 230, 29.0)
        """))

        print("4. Наполнение таблицы 'Строительные материалы'...")
        await conn.execute(text("""
            INSERT INTO materials (name, density, thermal_conductivity) VALUES
            ('Кирпич керамический пустотелый', 1400, 0.580),
            ('Железобетон', 2500, 1.920),
            ('Минераловатная плита (утеплитель)', 50, 0.045),
            ('Пенополистирол (EPS)', 30, 0.035),
            ('Дерево (сосна поперек волокон)', 500, 0.150)
        """))

        print("5. Наполнение таблицы 'Типы окон'...")
        await conn.execute(text("""
            INSERT INTO window_types (name, r_value, solar_factor) VALUES
            ('Двухкамерный обычный стеклопакет', 0.55, 0.65),
            ('Двухкамерный энергосберегающий (Low-E)', 0.75, 0.50),
            ('Однокамерный стеклопакет', 0.35, 0.75)
        """))

    print("✅ База данных успешно инициализирована и заполнена нормативными данными!")


if __name__ == "__main__":
    asyncio.run(seed_data())