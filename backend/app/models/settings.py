from tortoise import fields
from tortoise.models import Model


class Settings(Model):
    id = fields.IntField(pk=True)
    model_name = fields.CharField(max_length=255, default="deepseek-v4-pro")
    base_url = fields.CharField(max_length=512, default="https://api.deepseek.com/v1")
    api_key = fields.CharField(max_length=512, default="")
    tavily_key = fields.CharField(max_length=512, default="")
    proxy_url = fields.CharField(max_length=512, default="")
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "settings"

    @classmethod
    async def get_singleton(cls) -> "Settings":
        """Get or create the single settings row."""
        obj = await cls.first().only(
            "id", "model_name", "base_url", "api_key", "tavily_key", "proxy_url", "updated_at"
        )
        if obj is None:
            obj = await cls.create()
        return obj
