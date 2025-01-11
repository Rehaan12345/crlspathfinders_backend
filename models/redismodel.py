from upstash_redis import Redis
from dotenv import load_dotenv
import os, json, requests
from .model import get_collection, get_collection_python

load_dotenv()

redis = Redis(url=os.environ.get("REDIS_URL"), token=os.environ.get("REDIS_TOKEN"))


def format_json(docs):
    results = []
    for key, value in docs.items():
        # Decode the key and value if they are bytes
        key_str = key.decode("utf-8") if isinstance(key, bytes) else key
        value_str = value.decode("utf-8") if isinstance(value, bytes) else value

        # If value_str is a valid JSON string, load it into a Python dictionary
        try:
            # Try to parse the value as JSON
            data = json.loads(value_str)
        except json.JSONDecodeError:
            # If not valid JSON, just keep it as a string
            data = value_str

        # Append the transformed dictionary to the results list
        data["id"] = key_str
        results.append(data)

    # Sort the data list alphabetically by id
    results.sort(key=lambda x: x["id"])

    # Convert results to JSON string
    json_results = json.dumps(results)

    return json_results


def get_redis_cached_data(collection):
    try:
        docs = redis.hgetall(collection)  # Get field data from hash
        if docs:
            return format_json(docs)
        return None
    except Exception as e:
        print(f"Redis error: {e}")
        return None


# Function to set data in a Redis hash
def set_redis_cached_data(collection, data, expiry=3600):
    try:
        data = json.loads(data)
        for d in data:
            doc_id = d["id"]
            new_data = json.dumps(d)
            redis.hset(collection, doc_id, new_data)
        redis.expire(collection, expiry)  # Set an expiry time for the hash key
        return {"status": 0}
    except Exception as e:
        print(f"Redis error: {e}")
        return {"status": -1, "error_message": e}


def check_upstash_usage():
    """
    Fetch and check Upstash Redis usage limits.

    Returns:
        dict: Usage details including memory, bandwidth, and keys.
    """
    # Replace with your Upstash Redis REST URL and token
    upstash_url = os.getenv(
        "REDIS_URL"
    )  # e.g., "https://<your-instance>.upstash.io/usage"
    rest_token = os.getenv("REDIS_TOKEN")  # Your Upstash REST token

    if not upstash_url or not rest_token:
        return {"error": "Upstash URL or REST token is missing."}

    headers = {"Authorization": f"Bearer {rest_token}"}

    try:
        response = requests.get(upstash_url, headers=headers)
        response.raise_for_status()  # Raise an error for non-200 responses
        usage_data = response.json()
        return usage_data

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_redis_collection(collection):
    try:
        docs = redis.hgetall(collection)

        if docs:
            json_results = format_json(docs)

            return {"status": 0, "results": json_results}

        else:  # If the redis is not updated
            return {"status": -3, "error_message": "redis is empty"}

    except Exception as e:
        print(f"Error getting collection: {e}")
        return {"status": -1, "error_message": f"Failed to check redis: {e}"}


def get_redis_collection_id(collection, target_id):
    try:
        target_val = redis.hmget(collection, target_id)
        if target_val:
            return {"status": 0, "target_val": target_val}
        else:
            return {"status": -4, "error_message": "Collection id not found"}
    except Exception as e:
        return {
            "status": -1,
            "error_message": f"Failed to get redis collection id: {e}",
        }


def add_redis_collection(collection):
    try:
        new_coll = get_collection_python(collection)
        for c in new_coll:
            doc_id = c["id"]
            new_data = json.dumps(c)
            redis.hset(collection, doc_id, new_data)
        return {"status": 0, "collection": get_collection(collection)}
    except Exception as e:
        return {
            "status": -1,
            "error_message": f"Failed to add collection to redis: {e}",
        }


def add_redis_collection_id(
    collection, data, club_id="", mentor_id="", pml_id="", user_id=""
):
    try:
        if len(club_id) > 1:
            redis.hset(collection, club_id, data)
        elif len(mentor_id) > 1:
            redis.hset(collection, mentor_id, data)
        elif len(pml_id) > 1:
            redis.hset(collection, pml_id, data)
        elif len(user_id) > 1:
            redis.hset(collection, user_id, data)
        else:
            redis.hset(collection, data["id"], data)
        return {"status": 0}
    except Exception as e:
        return {
            "status": -1,
            "error_message": f"Failed to add redis collection id: {e}",
        }


def delete_redis_data(collection, id):
    try:
        delete = redis.hdel(collection, id)
        if delete == 1:
            return {"status": 0}
        if delete == 0:
            return {"status": -5, "error_message": "No redis field found to delete"}
    except Exception as e:
        return {"status": -1, "error_message": e}


def delete_redis_id(collection, delete_id):
    try:
        redis.hdel(collection, delete_id)
        return {"status": 0}
    except Exception as e:
        print(e)
        return {
            "status": -1,
            "error_message": f"Failed to delete redis collection id: {e}",
        }
