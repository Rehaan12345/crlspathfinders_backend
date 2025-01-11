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
import secrets, os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Annotated
from models.peermentormodel import (
    create_link,
    remove_link,
    update_link,
    update_category,
    create_category,
    delete_category,
)
from models.model import get_el_id, get_collection_id
from models.redismodel import add_redis_collection_id, delete_redis_id

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


router = APIRouter(tags=["peermentor"])


class Link(BaseModel):
    link_name: str
    link_url: str
    categories: List[str]
    bio: str
    deadline: str


@router.post("/addlink/")
async def add_link(link: Link, username: Annotated[str, Depends(get_current_username)]):
    try:
        # TO-DO later: Make sure the name is unique.
        create_link(
            link.link_name, link.link_url, link.categories, link.bio, link.deadline
        )
        pml_id = get_el_id("PeerMentorLinks", link.link_name)
        coll_id = get_collection_id("PeerMentorLinks", pml_id)
        add_id = add_redis_collection_id("PeerMentorLinks", coll_id, pml_id=pml_id)
        if add_id["status"] == 0:
            return {"status": "Successfully created pml"}
        return {"status": f"Failed to update pml redis: {add_id["error_message"]}"}
        # print(f"Successfully created pml link: {link.link_name}")
        # return {"status": "Successfully created pml link"}
    except Exception as e:
        print(f"Failed to create pml link: {e}")
        return {"status": f"Failed to create pml link: {e}"}


@router.get("/deletelink/{link_name}")
async def delete_link(
    link_name, username: Annotated[str, Depends(get_current_username)]
):
    try:
        pml_id = get_el_id("PeerMentorLinks", link_name)
        del_id = delete_redis_id("PeerMentorLinks", pml_id)
        if del_id["status"] == 0:
            remove_link(link_name)
            return {"status": "Successfully deleted pml"}
        return {"status": f"Failed to delete pml redis: {del_id["error_message"]}"}
    except Exception as e:
        print(f"Failed to delete link: {e}")
        return {"status": f"Failed to delete link: {e}"}


class EditLink(BaseModel):
    old_name: str
    new_name: str
    new_url: str
    categories: List[str]
    bio: str
    deadline: str


@router.post("/editlink/")
async def edit_link(
    edit_link: EditLink, username: Annotated[str, Depends(get_current_username)]
):
    try:
        update_link(
            edit_link.old_name,
            edit_link.new_name,
            edit_link.new_url,
            edit_link.categories,
            edit_link.bio,
            edit_link.deadline,
        )
        pml_id = get_el_id("PeerMentorLinks", edit_link.new_name)
        coll_id = get_collection_id("PeerMentorLinks", pml_id)
        add_id = add_redis_collection_id("PeerMentorLinks", coll_id, pml_id=pml_id)
        if add_id["status"] == 0:
            return {"status": "Successfully edited pml"}
        return {"status": f"Failed to update pml redis: {add_id["error_message"]}"}
    except Exception as e:
        print(f"Failed to edit link: {e}")
        return {"status": f"Failed to edit link: {e}"}


class EditCategory(BaseModel):
    old_cat_name: str
    new_cat_name: str


@router.post("/editcategory/")
def edit_category(
    edit_cat: EditCategory, username: Annotated[str, Depends(get_current_username)]
):
    update_category(edit_cat.old_cat_name, edit_cat.new_cat_name)
    pml_id = "PeerMentor"
    coll_id = get_collection_id("Demographics", pml_id)
    add_id = add_redis_collection_id("Demographics", coll_id, pml_id=pml_id)
    print(add_id)


class NewCategory(BaseModel):
    new_cat: str


@router.post("/addcategory")
def add_category(
    category: NewCategory, username: Annotated[str, Depends(get_current_username)]
):
    create_category(category.new_cat)
    pml_id = "PeerMentor"
    coll_id = get_collection_id("Demographics", pml_id)
    add_id = add_redis_collection_id("Demographics", coll_id, pml_id=pml_id)
    print(add_id)


@router.post("/deletecategory")
def add_category(
    category: NewCategory, username: Annotated[str, Depends(get_current_username)]
):
    delete_category(category.new_cat)
    pml_id = "PeerMentor"
    coll_id = get_collection_id("Demographics", pml_id)
    add_id = add_redis_collection_id("Demographics", coll_id, pml_id=pml_id)
    print(add_id)
