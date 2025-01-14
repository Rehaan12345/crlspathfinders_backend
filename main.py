from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.middleware.cors import CORSMiddleware
from cloudinary.utils import cloudinary_url
import os, sys, io
import json, tempfile, mimetypes
from fastapi.responses import StreamingResponse
from typing import List, Annotated
from datetime import timedelta
from pydantic import BaseModel
from models.model import (
    get_collection_id,
    get_collection,
    get_sub_collection,
    remove_id,
    get_collection_python,
)
from routers import user, club, mentor, peermentor, allinfo, libraryinfo
from requests_cache import CachedSession
from dotenv import load_dotenv
from sendmail import send_mail
from upstash_redis import Redis
from models.redismodel import (
    get_redis_collection,
    add_redis_collection,
    get_redis_collection_id,
    add_redis_collection_id,
    delete_redis_data,
)
from fastapi.responses import JSONResponse


load_dotenv()
curr_url = os.environ.get("CURR_URL")

# Redis testing:

redis = Redis(url=os.environ.get("REDIS_URL"), token=os.environ.get("REDIS_TOKEN"))

# from google.cloud import storage

# DO NOT IMPORT PYRBASE (GIVES THE MUTABLEMAPPING ERROR)!!!

# CORS Documentation: https://fastapi.tiangolo.com/tutorial/cors/

# Create virtual environment: python3 -m venv venv

app = FastAPI()

security = HTTPBasic()

# logfire.configure()
# logfire.instrument_fastapi(app)

# @app.get("/hello")
# async def hello(name: str):
#     return {"message": f"hello {name}"}

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://localhost:8080",
    "https://crlspathfinders-frontend.vercel.app",
    "https://www.crlspathfinders.com",
    "https://www.crlspathfinders.com/",
    "crlspathfinders.com",
    "crlspathfinders.com/",
    "https://crlspathfinders-backend.vercel.app",
    "https://crlspathfinders-backend.vercel.app/",
    "https://crlspathfinders-backend.vercel.app/cache/Mentors",
    "https://crlspathfinders-frontend-44w5k1duv-rehaan12345s-projects.vercel.app/",
    "https://crlspathfinders-frontend-exrq8i8v2-rehaan12345s-projects.vercel.app/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(club.router)
app.include_router(mentor.router)
app.include_router(peermentor.router)
app.include_router(allinfo.router)
app.include_router(libraryinfo.router)

# Model schemas:

# uvicorn main:app --reload
# Read a document:

# Caching:

# cached_mentors = CachedSession(
#     cache_name="cache/Mentors",
#     expire_after=10 # 10 s
# )

# cached_data = CachedSession(
#     backend='sqlite',
#     cache_name="cache.sqlite",  # SQLite database file
#     expire_after=10
# )

# @app.get("/cache/{collection}")
# def cache_mentors(collection: str):
#     print(f"{curr_url}read/{collection}")
#     data = cached_data.get(f"{curr_url}read/{collection}")
#     return data.json()


def get_current_username(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = bytes(os.environ.get("AUTH_USERNAME"), "utf-8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = bytes(os.environ.get("AUTH_PASSWORD"), "utf-8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/users/me")
def read_current_user(username: Annotated[str, Depends(get_current_username)]):
    return {"username": username}


@app.get("/")
def home(username: Annotated[str, Depends(get_current_username)]):
    print(username)
    return {"status": "rehaan"}


@app.get("/add/{num1}/{num2}")
def add_nums(
    num1: int, num2: int, username: Annotated[str, Depends(get_current_username)]
):
    result = num1 + num2
    return {"data": result}


@app.get("/testonetwothree")
def test():
    return {"hello": "world"}


@app.get("/read/{collection}/{id}")
async def read_document(
    collection: str, id: str, username: Annotated[str, Depends(get_current_username)]
):
    coll_id = get_redis_collection_id(collection, id)
    status = coll_id["status"]
    if status == 0:  # Found
        return {"status": 0, "collid": coll_id["target_val"]}
    if status == -4:  # No collection id found
        coll_id = get_collection_id(collection, id)
        add_id = add_redis_collection_id(collection, coll_id)
        if add_id["status"] == 0:
            return {"status": 0, "collid": coll_id}
        return {"status": -1, "error_message": add_id["error_message"]}
    if status == -1:
        return {"status": -1, "error_message": coll_id["error_message"]}


@app.get("/read/{collection}")
async def read_collection(
    collection: str, username: Annotated[str, Depends(get_current_username)]
):
    try:
        redis_collection = get_redis_collection(collection)
        status = redis_collection["status"]

        print(f"status: {status}, collection: {collection}")

        if status == 0:  # Found
            # logging.info(f"Collection '{collection}' found in Redis.")
            return {"status": 0, "collection": redis_collection["results"]}

        if status == -3:  # No cache (collection not in Redis)
            # logging.warning(f"Collection '{collection}' not found in Redis. Adding to cache.")
            # If not in cache, then add it to cache
            add_collection = add_redis_collection(collection)
            if add_collection["status"] == 0:
                # logging.info(f"Collection '{collection}' successfully added to Redis.")
                return {"status": 0, "collection": add_collection["collection"]}
            error_message = add_collection["error_message"]
            # logging.error(f"Failed to add collection '{collection}' to Redis: {error_message}")
            return {"status": -1, "error_message": error_message}

        if status == -1:
            error_message = redis_collection["error_message"]
            # logging.error(f"Error retrieving collection '{collection}' from Redis: {error_message}")
            return {"status": -1, "error_message": error_message}

    except Exception as e:
        # logging.critical(f"Critical error in read_collection function for '{collection}': {str(e)}")
        return {"status": -1, "error_message": "An unexpected error occurred."}


# @app.get("/read/{collection}")
# async def read_collection(collection: str):
#     # Attempt to retrieve the collection from Redis
#     redis_collection = get_redis_collection(collection)
#     status = redis_collection["status"]

#     if status == 0:  # Found in cache
#         response = {"status": 0, "collection": redis_collection["results"]}
#         # Add Cache-Control headers to allow caching
#         headers = {"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
#         print(headers)
#         return JSONResponse(content=response, headers=headers)

#     if status == -3:  # Not in cache (Redis miss)
#         # Attempt to add the collection to Redis
#         add_collection = add_redis_collection(collection)
#         if add_collection["status"] == 0:
#             response = {"status": 0, "collection": add_collection["collection"]}
#             headers = {"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
#             return JSONResponse(content=response, headers=headers)
#         # Return error if adding to Redis fails
#         response = {"status": -1, "error_message": add_collection["error_message"]}
#         headers = {"Cache-Control": "no-store"}  # Avoid caching errors
#         return JSONResponse(content=response, headers=headers)

#     if status == -1:  # General error from Redis
#         response = {"status": -1, "error_message": redis_collection["error_message"]}
#         headers = {"Cache-Control": "no-store"}  # Avoid caching errors
#         return JSONResponse(content=response, headers=headers)


# Read a sub-collection
@app.get("/read/{collection}/{id}/{subcollection}")
async def read_sub_collection(
    collection: str,
    id: str,
    subcollection: str,
    username: Annotated[str, Depends(get_current_username)],
):
    return get_sub_collection(collection, id, subcollection)


# Delete (delete the document itself, not the info, so only need the document parameter):
@app.get("/delete/{collection}/{id}")
async def delete_info(
    collection: str, id: str, username: Annotated[str, Depends(get_current_username)]
):
    del_redis = delete_redis_data(collection, id)
    print(del_redis)
    return remove_id(collection, id)


class SendMassEmail(BaseModel):
    collection: str
    subject: str
    body: str
    recipients: List[str]


@app.post("/emailall/")
def email_all(
    email: SendMassEmail, username: Annotated[str, Depends(get_current_username)]
):
    sendees = get_collection_python(email.collection)
    emails = []
    if email.collection == "Rehaan":
        print("rehaan found")
        send_mail("25ranjaria@cpsd.us", email.subject, email.body)
        return {"status": 0}
    if email.collection == "Clubs":
        for s in sendees:
            emails.append(s["president_email"])
            if len(s["vice_presidents_emails"]) > 0:
                for v in s["vice_presidents_emails"]:
                    emails.append(v)
        try:
            send_mail(emails, email.subject, email.body)
            return {"status": 0}
        except Exception as e:
            return {"status": -1, "error_message": e}
    else:
        for s in sendees:
            emails.append(s["email"])
        try:
            send_mail(emails, email.subject, email.body)
            return {"status": 0}
        except Exception as e:
            return {"status": -1, "error_message": e}


@app.get("/emailone/{subject}/{body}/{receiver}")
def email_one(
    subject: str,
    body: str,
    receiver: str,
    username: Annotated[str, Depends(get_current_username)],
):
    try:
        send_mail(receiver, subject, body)
        print("sent email successfully")
        return {"status": 0}
    except Exception as e:
        return {"status": -1, "error_message": e}
