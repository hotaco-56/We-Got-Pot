from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):
    day: str
    hour: int

current_time = Timestamp
days_of_week = ['Edgeday', 'Bloomday', 'Arcanaday', 'Hearthday', 'Crownday', 'Blesseday', 'Soulday']

@router.post("/current_time")
def post_time(timestamp: Timestamp):
    """
    Share current time.
    """
    print(timestamp)
    current_time.day = timestamp.day
    current_time.hour = timestamp.hour

    return "OK"

