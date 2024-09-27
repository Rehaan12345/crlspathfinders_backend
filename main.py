from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from cloudinary.utils import cloudinary_url
import os, sys, io
import json, tempfile, mimetypes
from fastapi.responses import StreamingResponse
from typing import List
from datetime import timedelta
from pydantic import BaseModel
from models.model import get_collection_id, get_collection, get_sub_collection, remove_id
from routers import user, club, mentor, peermentor

# from google.cloud import storage

# DO NOT IMPORT PYRBASE (GIVES THE MUTABLEMAPPING ERROR)!!!

# CORS Documentation: https://fastapi.tiangolo.com/tutorial/cors/

# Create virtual environment: python3 -m venv venv

app = FastAPI()

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
    "https://crlspathfinders-backend.vercel.app/"
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

# Model schemas:

# uvicorn main:app --reload
# Read a document:

@app.get("/")
def home():
    return {"status": "rehaan"}

@app.get("/testonetwothree")
def test():
    return {"hello": "world"}

@app.get("/read/{collection}/{id}")
async def read_document(collection: str, id: str):
    return get_collection_id(collection, id)

# Read a collection:
@app.get("/read/{collection}")
async def read_collection(collection: str):
    return get_collection(collection)

# Read a sub-collection
@app.get("/read/{collection}/{id}/{subcollection}")
async def read_sub_collection(collection: str, id: str, subcollection: str):
    return get_sub_collection(collection, id, subcollection)

# Delete (delete the document itself, not the info, so only need the document parameter):
@app.get("/delete/{collection}/{id}")
async def delete_info(collection: str, id: str):
    return remove_id(collection, id)