from sqlalchemy import Column, Boolean, SmallInteger, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..db import Base

class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"))
    is_correct = Column(Boolean)
    num_attempts = Column(SmallInteger)
    time_spent_secs = Column(Integer)
    hints_used = Column(SmallInteger, default=0)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id"))
