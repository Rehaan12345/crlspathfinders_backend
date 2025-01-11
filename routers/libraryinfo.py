from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Depends,
    HTTPException,
    status,
    APIRouter,
    Form,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, os, httpx
from pydantic import BaseModel
from typing import List, Optional, Annotated
from models.clubmodel import (
    make_club,
    change_club,
    update_status,
    remove_club,
    verify_club_model,
    upload_club_image,
    delete_club_image,
    set_club_image_doc,
)
from models.model import (
    get_collection_python,
    get_el_id,
    get_doc,
    get_collection,
    get_collection_id,
)
from models.redismodel import add_redis_collection_id, delete_redis_id
from models.usermodel import join_leave_club
from sendmail import send_mail
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


router = APIRouter(tags=["libraryinfo"])


@router.get("/getlibraryinfo/")
async def get_library_info(username: Annotated[str, Depends(get_current_username)]):
    try:
        url = os.environ.get("LIBRARY_INFO_URL")
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise exception for HTTP errors
            return {"status": 0, "data": response.json()}
    except Exception as e:
        return {"status": -1, "error_message": e}
