from sqlalchemy import Table, Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from ..db import Base


user_classroom = Table(
    "user_classroom",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("class_id", UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True),
)
