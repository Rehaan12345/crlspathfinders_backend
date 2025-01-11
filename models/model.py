import firebase_admin, json, os
from firebase_admin import credentials, storage
from firebase_admin import firestore
from dotenv import load_dotenv

load_dotenv()

cred = credentials.Certificate(json.loads(os.environ.get("FIREBASE_ACCOUNT_KEY")))
firebase_admin.initialize_app(
    cred, {"storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET")}
)

firebaseConfig = {
    "apiKey": os.environ.get("FIREBASE_API_KEY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.environ.get("FIREBASE_APP_ID"),
    "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID"),
}

db = firestore.client()  # connecting to firestore
from upstash_redis import Redis

redis = Redis(
    url="https://welcomed-kiwi-27133.upstash.io", token=os.environ.get("REDIS_TOKEN")
)


def get_el_id(collection, target):
    # target is club_name (Clubs) or email (Users & Mentors)

    if collection == "Clubs":
        collection = db.collection(collection)
        docs = collection.get()
        results = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict["id"] = doc.id
            results.append(doc_dict)
        for r in results:
            if r["secret_password"] == target:
                return r["id"]
    elif collection == "Users" or collection == "Mentors":
        collection = db.collection(collection)
        docs = collection.get()
        results = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict["id"] = doc.id
            results.append(doc_dict)
        for r in results:
            if r["email"] == target:
                return r["id"]
    elif collection == "PeerMentorLinks":
        collection = db.collection(collection)
        docs = collection.get()
        results = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict["id"] = doc.id
            results.append(doc_dict)
        for r in results:
            if r["name"] == target:
                return r["id"]


def get_collection_id(collection, id):
    try:
        result = db.collection(collection).document(id).get().to_dict()
        return result
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


def get_collection(collection):
    collection = db.collection(collection)
    docs = collection.get()
    results = []
    for doc in docs:
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        results.append(doc_dict)

    # print(f"Before: {results}")

    json_results = json.dumps(results)

    return json_results


def get_collection_python(collection):
    collection = db.collection(collection)
    docs = collection.get()
    results = []
    for doc in docs:
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        results.append(doc_dict)

    return results


def get_sub_collection(collection, id, subcollection):
    try:
        docs = db.collection(collection).document(id).collection(subcollection).get()
        results = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict["id"] = doc.id
            results.append(doc_dict)

        # print(f"Before: {results}")

        json_results = json.dumps(results)

        return json_results
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


def remove_id(collection, id):
    try:
        db.collection(collection).document(id).delete()
        return {"status": "Success"}
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


def get_doc(collection, doc):
    try:
        result = db.collection(collection).document(doc).get().to_dict()
        return result
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}
