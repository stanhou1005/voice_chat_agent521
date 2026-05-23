"""
Session metadata model — stores the "history list" data for the sidebar.
Managed by Tortoise-ORM (not LangGraph Store), for reliable SQL querying.
"""

from tortoise import fields
from tortoise.models import Model


class SessionMeta(Model):
    thread_id = fields.CharField(max_length=64, pk=True, description="LangGraph thread_id")
    title = fields.CharField(max_length=255, default="新会话")
    created_at = fields.DatetimeField(auto_now_add=True)
    last_active_at = fields.DatetimeField(auto_now=True)
    message_count = fields.IntField(default=0)

    class Meta:
        table = "session_meta"
        ordering = ["-last_active_at"]
