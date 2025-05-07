from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()

def ungroup_threads_message(mongo_url, collection_name):

    client = MongoClient(mongo_url)
    filter={}
    project={
        'content' : 1
    }

    result = client[collection_name]['threads'].find(
    filter=filter,
    projection=project
    )

    def stevefunk(content, parent_id=None):
        id = content.get("id", "")
        
        children = content.get("children", [])
        endorsed_responses = content.get('endorsed_reponses',[])
        non_endorsed_responses = content.get('non_endorsed_reponses',[])
        
        content['_id'] = id
        if content.get("depth", 0) == 1:
            content["parent_id"] = parent_id

        result = client[collection_name]['documents'].find_one({'_id' : id})
        if result is None:
            client[collection_name]['documents'].insert_one(content)
        
        for doc in children:
            stevefunk(doc, parent_id=id)
        
        for doc in endorsed_responses:
            stevefunk(doc, parent_id=id)

        for doc in non_endorsed_responses:
            stevefunk(doc, parent_id=id)

    for doc in result:
        content = doc["content"]
        stevefunk(content)

if __name__ == "__main__":
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        raise ValueError("MONGO_URL environment variable is not set")
    collection_name = "G1"
    ungroup_threads_message(mongo_url=mongo_url, collection_name=collection_name)
    print("Ungrouping threads done")