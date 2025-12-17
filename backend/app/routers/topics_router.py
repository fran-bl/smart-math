from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.topics import Topic

router = APIRouter(prefix="/topics", tags=["topics"])

db_dependency = Annotated[Session, Depends(get_db)]


@router.get("/", summary="Get all topics")
def get_all_topics(db: db_dependency):
    """
    Dohvaća sve teme (topics) iz baze podataka.
    """
    topics = db.query(Topic).all()

    return [
        {
            "id": str(topic.id),
            "name": topic.name,
        }
        for topic in topics
    ]
