from pymongo import MongoClient
import config

# MongoDB configuration
mongo_client = MongoClient(config.MONGODB_URI)  
db = mongo_client[config.DB_NAME]

def check_and_create_group_collection(group_name: str):
    if group_name not in db.list_collection_names():
        db.create_collection(group_name)
        print(f"Created collection: {group_name}")
    else:
        print(f"Collection {group_name} already exists.")

def save_message_group_entry(group_name: str, message_group_entry: list):
    check_and_create_group_collection(group_name)
    collection = db[group_name]
    collection.insert_one({"messages": message_group_entry})
    print("Saved message group entry to database.")

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
        print(f"No entry found for message ID: {message_id} in group: {group_name}")
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
        print(f"No entry found for thread ID: {thread_id} in group: {group_name}")
        return None