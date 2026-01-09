from sqlalchemy import Column, Text, TIMESTAMP, CheckConstraint, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from ..db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, nullable=False, unique = True)
    password = Column(Text)  # optional: teacher ima, student nema
    role = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    current_difficulty = Column(SmallInteger, nullable=False, default=3) #početni difficulty za svakog učenika je 3 da ga možemo odmah i dizati i spuštati

    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty_check"),
        CheckConstraint("role IN ('student','teacher')", name="role_check"),
    )