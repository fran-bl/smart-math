
from xmlrpc.client import Boolean
from sqlalchemy import Column, ForeignKey, TIMESTAMP, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from ..db import Base

class GamePlayers(Base):
    __tablename__ = "game_players"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("game.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    socket_id = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)

    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    left_at = Column(TIMESTAMP(timezone=True))