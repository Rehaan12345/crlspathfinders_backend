from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, os
from pydantic import BaseModel
from typing import List, Optional, Annotated
from models.allinfomodel import (
    update_all_info_collection,
    add_document_to_all_info_collection,
)
from models.redismodel import add_redis_collection
from dotenv import load_dotenv

load_dotenv()

security = HTTPBasic()


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


router = APIRouter(tags=["allinfo"])


class UpdateAllInfo(BaseModel):
    doc: str
    vals: dict


@router.post("/update/")
def update_all_info(
    update: UpdateAllInfo, username: Annotated[str, Depends(get_current_username)]
):
    result = update_all_info_collection(update.doc, update.vals)
    add_redis_collection("AllInfo")
    if result["status"] == 0:
        return {"status": 0}
    print(result)
    return {"status": -1, "error_message": result["error_message"]}


class AddDocument(BaseModel):
    doc: dict


@router.post("/adddocument/")
def add_document(
    doc: AddDocument, username: Annotated[str, Depends(get_current_username)]
):
    result = add_document_to_all_info_collection(doc.doc)
    if result["status"] == 0:
        add_redis_collection("AllInfo")
        return {"status": 0}
    return {"status": -1, "error_message": result["error_message"]}
