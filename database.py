import os
import urllib.parse
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost").strip("'\" ")
DB_PORT = os.getenv("DB_PORT", "3306").strip("'\" ")
DB_USER = os.getenv("DB_USER", "root").strip("'\" ")
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip("'\" ")
DB_NAME = os.getenv("DB_NAME", "Data").strip("'\" ")

encoded_password = urllib.parse.quote(DB_PASSWORD)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+aiomysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

