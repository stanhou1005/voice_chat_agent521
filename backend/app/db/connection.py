from tortoise import Tortoise
from app.config import DATABASE_URL

MODELS = ["app.models.settings"]


async def init_db():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": MODELS},
    )
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()
