"""User model for authentication."""

from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=128, unique=True)
    password_hash = fields.CharField(max_length=256)
    role = fields.CharField(max_length=16, default="user")  # "admin" or "user"
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
