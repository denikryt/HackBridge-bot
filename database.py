from pymongo import MongoClient
import config
from logger_config import get_logger

logger = get_logger(__name__)

# MongoDB configuration
mongo_client = MongoClient(config.MONGODB_URI)  
db = mongo_client[config.DB_NAME]

def check_and_create_group_collection(group_name: str):
    if group_name not in db.list_collection_names():
        db.create_collection(group_name)
        logger.info(f"Created collection: {group_name}")
    else:
        logger.info(f"Collection {group_name} already exists.")

def save_message_group_entry(group_name: str, message_group_entry: list):
    check_and_create_group_collection(group_name)
    collection = db[group_name]
    collection.insert_one({"messages": message_group_entry})
    logger.info("Saved message group entry to database.")

def get_message_group_entry_by_message_id(message_id: str, group_name: str):
    if not type(message_id) is str:
        message_id = str(message_id)

    check_and_create_group_collection(group_name)
    collection = db[group_name]
    result = collection.find_one({
        "messages": {
            "$elemMatch": {
                "message_id": message_id
            }
        }
    })
    if result:
        return result["messages"]
    else:
        logger.info(f"No entry found for message ID: {message_id} in group: {group_name}")
        return None

def get_thread_message_group_entry(thread_id: str, group_name: str):
    """Get message group entry for a specific thread."""
    if not type(thread_id) is str:
        thread_id = str(thread_id)

    check_and_create_group_collection(group_name)
    collection = db[group_name]
    result = collection.find_one({
        "messages": {
            "$elemMatch": {
                "thread_id": thread_id
            }
        }
    })
    if result:
        return result["messages"]
    else:
        logger.info(f"No entry found for thread ID: {thread_id} in group: {group_name}")
        return None

def delete_message_group_entry_by_message_id(message_id: str, group_name: str):
    """Delete message group entry by message ID."""
    if not type(message_id) is str:
        message_id = str(message_id)

    check_and_create_group_collection(group_name)
    collection = db[group_name]
    result = collection.delete_one({
        "messages": {
            "$elemMatch": {
                "message_id": message_id
            }
        }
    })
    if result.deleted_count > 0:
        logger.info(f"Deleted message group entry for message ID: {message_id} in group: {group_name}")
        return True
    else:
        logger.info(f"No entry found to delete for message ID: {message_id} in group: {group_name}")
        return False