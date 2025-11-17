from sqlalchemy import Column, Text, SmallInteger, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..db import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False)
    difficulty = Column(SmallInteger, nullable=False, default=1)
    type = Column(Text, nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"))

    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty_check"),
        CheckConstraint("type IN ('mcq','num','wri')", name="type_check"),
    )
