from sqlalchemy import Column, TIMESTAMP, SmallInteger, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from ..db import Base

class Round(Base):
    __tablename__ = "rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    game_id = Column(UUID(as_uuid=True), ForeignKey("game.id", ondelete="SET NULL"))
    start_ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
    end_ts = Column(TIMESTAMP(timezone=True))
    question_count = Column(SmallInteger)
    accuracy = Column(Numeric)  # 0..1
    avg_time_secs = Column(Numeric)
    hint_rate = Column(Numeric)
