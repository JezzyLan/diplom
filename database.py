# database.py - Модуль конфигурации подключения к базе данных
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

# Строка подключения к PostgreSQL (асинхронный драйвер asyncpg)
DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/heat_db"

# Настройка асинхронного движка SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=False)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Зависимость (Dependency Injection) для получения сессии БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session