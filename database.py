import copy
from pymongo import MongoClient
import config
from logger_config import get_logger

logger = get_logger(__name__)

# MongoDB configuration
mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.DB_NAME]

ROLES_STATE_DOC_ID = "roles_state"
REGISTERED_CHANNELS_STATE_DOC_ID = "registered_channels_state"
LINKED_CHANNEL_GROUPS_STATE_DOC_ID = "linked_channel_groups_state"

DEFAULT_ROLES_STATE = {
    "superadmins": [],
    "admins": [],
    "registrators": [],
}

DEFAULT_REGISTERED_CHANNELS_STATE = {
    "register": [],
}

DEFAULT_LINKED_CHANNEL_GROUPS_STATE = {
    "groups": [],
}


def _get_state_document(collection_name: str, doc_id: str, default_state: dict):
    collection = db[collection_name]
    result = collection.find_one({"_id": doc_id}, {"_id": 0})
    if result is None:
        return copy.deepcopy(default_state)
    return result


def _save_state_document(collection_name: str, doc_id: str, state: dict):
    collection = db[collection_name]
    document = {"_id": doc_id, **state}
    collection.replace_one({"_id": doc_id}, document, upsert=True)


def ensure_state_documents():
    """Ensure singleton state documents exist for legacy JSON-backed data."""
    db[config.ROLES_COLLECTION_NAME].update_one(
        {"_id": ROLES_STATE_DOC_ID},
        {"$setOnInsert": {"_id": ROLES_STATE_DOC_ID, **copy.deepcopy(DEFAULT_ROLES_STATE)}},
        upsert=True,
    )
    db[config.REGISTERED_CHANNELS_COLLECTION_NAME].update_one(
        {"_id": REGISTERED_CHANNELS_STATE_DOC_ID},
        {"$setOnInsert": {"_id": REGISTERED_CHANNELS_STATE_DOC_ID, **copy.deepcopy(DEFAULT_REGISTERED_CHANNELS_STATE)}},
        upsert=True,
    )
    db[config.LINKED_CHANNEL_GROUPS_COLLECTION_NAME].update_one(
        {"_id": LINKED_CHANNEL_GROUPS_STATE_DOC_ID},
        {"$setOnInsert": {"_id": LINKED_CHANNEL_GROUPS_STATE_DOC_ID, **copy.deepcopy(DEFAULT_LINKED_CHANNEL_GROUPS_STATE)}},
        upsert=True,
    )


def load_roles_state():
    return _get_state_document(
        config.ROLES_COLLECTION_NAME,
        ROLES_STATE_DOC_ID,
        DEFAULT_ROLES_STATE,
    )


def save_roles_state(state: dict):
    _save_state_document(config.ROLES_COLLECTION_NAME, ROLES_STATE_DOC_ID, state)


def load_registered_channels_state():
    return _get_state_document(
        config.REGISTERED_CHANNELS_COLLECTION_NAME,
        REGISTERED_CHANNELS_STATE_DOC_ID,
        DEFAULT_REGISTERED_CHANNELS_STATE,
    )


def save_registered_channels_state(state: dict):
    _save_state_document(
        config.REGISTERED_CHANNELS_COLLECTION_NAME,
        REGISTERED_CHANNELS_STATE_DOC_ID,
        state,
    )


def load_linked_channel_groups_state():
    return _get_state_document(
        config.LINKED_CHANNEL_GROUPS_COLLECTION_NAME,
        LINKED_CHANNEL_GROUPS_STATE_DOC_ID,
        DEFAULT_LINKED_CHANNEL_GROUPS_STATE,
    )


def save_linked_channel_groups_state(state: dict):
    _save_state_document(
        config.LINKED_CHANNEL_GROUPS_COLLECTION_NAME,
        LINKED_CHANNEL_GROUPS_STATE_DOC_ID,
        state,
    )

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

def set_user_avatar(user_id: str, emoji_avatar: str):
    """Set emoji avatar for a user."""
    if not type(user_id) is str:
        user_id = str(user_id)

    collection = db[config.AVATAR_COLLECTION_NAME]
    # Upsert - update if exists, insert if not
    result = collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "emoji_avatar": emoji_avatar}},
        upsert=True
    )
    
    if result.upserted_id:
        logger.info(f"Created new avatar entry for user {user_id}: {emoji_avatar}")
    else:
        logger.info(f"Updated avatar for user {user_id}: {emoji_avatar}")
    
    return True

def get_user_avatar(user_id: str):
    """Get emoji avatar for a user."""
    if not type(user_id) is str:
        user_id = str(user_id)

    collection = db[config.AVATAR_COLLECTION_NAME]
    result = collection.find_one({"user_id": user_id})
    
    if result:
        logger.debug(f"Found avatar for user {user_id}: {result['emoji_avatar']}")
        return result["emoji_avatar"]
    else:
        logger.debug(f"No avatar found for user {user_id}")
        return None

def delete_user_avatar(user_id: str):
    """Delete emoji avatar for a user."""
    if not type(user_id) is str:
        user_id = str(user_id)

    collection = db[config.AVATAR_COLLECTION_NAME]
    result = collection.delete_one({"user_id": user_id})
    
    if result.deleted_count > 0:
        logger.info(f"Deleted avatar for user {user_id}")
        return True
    else:
        logger.info(f"No avatar found to delete for user {user_id}")
        return False

def _forum_thread_collection_name(group_name: str) -> str:
    return f"{group_name}_forum_threads"

def save_forum_thread_group_entry(group_name: str, thread_group_entry: list):
    collection_name = _forum_thread_collection_name(group_name)
    check_and_create_group_collection(collection_name)
    collection = db[collection_name]
    collection.insert_one({"threads": thread_group_entry})
    logger.info("Saved forum thread group entry to database.")

def get_forum_thread_group_entry_by_thread_id(thread_id: str, group_name: str):
    if not type(thread_id) is str:
        thread_id = str(thread_id)

    collection_name = _forum_thread_collection_name(group_name)
    check_and_create_group_collection(collection_name)
    collection = db[collection_name]
    result = collection.find_one({
        "threads": {
            "$elemMatch": {
                "thread_id": thread_id
            }
        }
    })
    if result:
        return result["threads"]
    else:
        logger.info(f"No forum thread entry found for thread ID: {thread_id} in group: {group_name}")
        return None

def delete_forum_thread_group_entry_by_thread_id(thread_id: str, group_name: str):
    if not type(thread_id) is str:
        thread_id = str(thread_id)

    collection_name = _forum_thread_collection_name(group_name)
    check_and_create_group_collection(collection_name)
    collection = db[collection_name]
    result = collection.delete_one({
        "threads": {
            "$elemMatch": {
                "thread_id": thread_id
            }
        }
    })
    if result.deleted_count > 0:
        logger.info(f"Deleted forum thread group entry for thread ID: {thread_id} in group: {group_name}")
        return True
    else:
        logger.info(f"No forum thread entry found to delete for thread ID: {thread_id} in group: {group_name}")
        return False
