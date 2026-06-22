import logging

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from app.config import config

logger = logging.getLogger(__name__)


async def get_checkpointer():
    client = MongoClient(config.mongo_uri)
    # The graph compilation allows passing a sync checkpointer to async code; it will run in an executor.
    saver = MongoDBSaver(client, db_name="cardflow")
    return saver
