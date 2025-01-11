from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Depends,
    HTTPException,
    status,
    APIRouter,
    Form,
    Request,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets, os
from dotenv import load_dotenv
from pydantic import BaseModel
from models.usermodel import (
    make_user,
    change_user,
    verify_token,
    get_current_user,
    get_user_from_email,
    join_leave_club,
    change_user_role,
    delete_user,
    change_is_leader,
    change_is_mentor,
    change_mentor_eligible,
    get_mentees,
)
from typing import Annotated, List
from models.model import get_el_id, get_doc, get_collection_python, get_collection_id
from models.clubmodel import get_members, manage_members, get_secret_pass
from models.redismodel import add_redis_collection_id, delete_redis_id
import json

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


router = APIRouter(tags=["user"])


class User(BaseModel):
    email: str
    is_leader: bool
    role: str
    leading: List[str]
    joined_clubs: List[str]


@router.post("/createuser/")
async def create_user(
    user: User, username: Annotated[str, Depends(get_current_username)]
):
    use = make_user(
        user.email, user.is_leader, user.role, user.leading, user.joined_clubs
    )
    user_id = get_el_id("Users", user.email)
    coll_id = get_collection_id("Users", user_id)
    add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
    return use


@router.post("/updateuser/")
async def update_user(
    user: User, username: Annotated[str, Depends(get_current_username)]
):
    chan = change_user(user.email, user.is_leader, user.role)
    user_id = get_el_id("Users", user.email)
    coll_id = get_collection_id("Users", user_id)
    add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
    return chan


class Token(BaseModel):
    token: str


@router.post("/verify-token")
def verify_token_route(token: Token):
    decoded_token = verify_token(token.token)
    return {"uid": decoded_token["uid"], "email": decoded_token.get("email")}


@router.get("/protected")
def protected_route(
    request: Request, username: Annotated[str, Depends(get_current_username)]
):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = auth_header.split("Bearer ")[-1]
    decoded_token = verify_token(token)
    return {"message": "You are authorized", "user_id": decoded_token["uid"]}


# New endpoint to handle additional user creation logic
@router.post("/create-user")
def create_user_route(
    token: Token, username: Annotated[str, Depends(get_current_username)]
):
    # Creates / adds the user into the Google Firebase Authentication:
    decoded_token = verify_token(token.token)
    # Creates / adds the user into the Google Firebase Firestore Database:
    # user = User()
    print(f"successfully created user: {decoded_token['uid']}")
    return {"status": "User created successfully", "user_id": decoded_token["uid"]}


@router.post("/make-user")
def make_new_user(user: User, username: Annotated[str, Depends(get_current_username)]):
    try:
        make_user(
            user.email, user.is_leader, user.role, user.leading, user.joined_clubs
        )
        user_id = get_el_id("Users", user.email)
        coll_id = get_collection_id("Users", user_id)
        add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
        return {"status": "Successfully made user"}
    except Exception as e:
        return {"status": f"Failed to make user: {e}"}


@router.get("/user-info")
def get_user_info(current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    uid = current_user.get("uid")
    # Create the User document in Firestore here.
    return {"uid": uid, "email": email}


@router.get("/getuserdocdata/{email}")
def get_user_doc_data(
    email: str, username: Annotated[str, Depends(get_current_username)]
):
    print("starting getuserdocdata")
    try:
        return get_user_from_email(email)
    except Exception as e:
        return {"status": f"Faield to getuserdocfromdata: {e}"}


@router.get("/toggleclub/{email}/{club_id}")
def toggle_club(
    email: str, club_id: str, username: Annotated[str, Depends(get_current_username)]
):
    user = get_user_from_email(email)
    # print("---------------------------")
    # print(user)
    # print("---------------------------")
    # print(user[0])
    # print("---------------------------")
    # print(json.loads(user[0]))
    # print("---------------------------")
    # temp = json.loads(user[0])
    # print(temp["joined_clubs"])
    clubs = json.loads(user[0])["joined_clubs"]
    print(clubs)

    members = get_members(club_id)
    secret_password = get_secret_pass(club_id)

    if club_id in clubs:
        try:
            join_leave_club("leave", email, club_id)
            members.remove(email)
            manage_members(secret_password, members)
            user_id = get_el_id("Users", email)
            coll_id = get_collection_id("Users", user_id)
            add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
            coll_id = get_collection_id("Clubs", club_id)
            add_id = add_redis_collection_id("Clubs", coll_id, club_id=club_id)
            return {"status": "Successfully left club"}
        except Exception as e:
            return {"status": f"Failed to leave club: {e}"}
    else:
        try:
            join_leave_club("join", email, club_id)
            members.append(email)
            manage_members(secret_password, members)
            user_id = get_el_id("Users", email)
            coll_id = get_collection_id("Users", user_id)
            add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
            coll_id = get_collection_id("Clubs", club_id)
            add_id = add_redis_collection_id("Clubs", coll_id, club_id=club_id)
            return {"status": "Successfully joined club"}
        except Exception as e:
            return {"status": f"Failed to join club: {e}"}


class ChangeRole(BaseModel):
    email: str
    new_role: str


@router.post("/changerole")
def change_role(
    change: ChangeRole, username: Annotated[str, Depends(get_current_username)]
):
    try:
        change_user_role(change.email, change.new_role)
        user_id = get_el_id("Users", change.email)
        coll_id = get_collection_id("Users", user_id)
        add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
        return {"status": "Successfully changed user role"}
    except Exception as e:
        print(f"Failed to change role: {e}")
        return {"status": f"Failed to change user role: {e}"}


@router.get("/deleteuser/{email}")
def remove_user(email: str, username: Annotated[str, Depends(get_current_username)]):
    try:
        user_id = get_el_id("Users", email)
        del_id = delete_redis_id("Users", user_id)
        if del_id["status"] == 0:
            print("status 0, deleting user")
            delete_user(email)
        return {"status": "Successfully deleted user"}
    except Exception as e:
        print(f"Failed to delete user: {e}")
        return {"status": f"Failed to delete user: {e}"}


class ToggleLeaderMentor(BaseModel):
    email: str
    leader_mentor: str
    toggle: bool


@router.post("/toggleleadermentor")
def toggle_leader_mentor(
    toggle: ToggleLeaderMentor, username: Annotated[str, Depends(get_current_username)]
):
    if toggle.leader_mentor == "Leader":
        try:
            change_is_leader(toggle.email, toggle.toggle)
            user_id = get_el_id("Users", toggle.email)
            coll_id = get_collection_id("Users", user_id)
            add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
            print(f"Changed {toggle.email} to {toggle.toggle}")
            return {"status": "Successfully toggled leader"}
        except Exception as e:
            print(f"Failed to toggle leader: {e}")
            return {"status": f"Failed to toggle leader: {e}"}
    if toggle.leader_mentor == "Mentor":
        try:
            change_is_mentor(toggle.email, toggle.toggle)
            user_id = get_el_id("Users", toggle.email)
            coll_id = get_collection_id("Users", user_id)
            add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
            print(f"Changed {toggle.email} to {toggle.toggle}")
            return {"status": "Successfully toggled mentor"}
        except Exception as e:
            print(f"Failed to toggle mentor: {e}")
            return {"status": f"Failed to toggle mentor: {e}"}
    if toggle.leader_mentor == "Mentor-Eligible":
        try:
            change_mentor_eligible(toggle.email, toggle.toggle)
            user_id = get_el_id("Users", toggle.email)
            coll_id = get_collection_id("Users", user_id)
            add_id = add_redis_collection_id("Users", coll_id, user_id=user_id)
            print(f"Changed {toggle.email} to {toggle.toggle}")
            return {"status": "Successfully toggled mentor eligible"}
        except Exception as e:
            print(f"Failed to toggle mentor eligible: {e}")
            return {"status": f"Failed to toggle mentor eligible: {e}"}
    print(f"Wrong / not enough parameters in toggle leader mentor ok.")
    return {"status": "Incorrect parameters"}


@router.get("/getmentees")
def read_mentees(username: Annotated[str, Depends(get_current_username)]):
    pairings = []
    mentees = get_mentees()
    mentors = get_collection_python("Mentors")

    for m in mentors:
        curr_mentor = m
        curr_mentor_catalog = curr_mentor["hours_worked_catalog"]
        for c in curr_mentor_catalog:
            curr_catalog = c
            if curr_catalog["status"] == 0:
                catalog_id = c["id"]
                for ment in mentees:
                    curr_mentee = ment
                    mentee_logs = curr_mentee["mentee_logs"]
                    entry = None
                    for l in mentee_logs:
                        if catalog_id == l["id"]:
                            entry = {
                                "mentee": curr_mentee["email"],
                                "mentor": curr_mentor["email"],
                                "mentee_description": l["description"],
                                "mentor_description": curr_catalog["description"],
                                "hours": curr_catalog["hours"],
                                "date_confirmed": l["date_confirmed"],
                                "date_met": l["date_met"],
                            }
                            pairings.append(entry)
            elif curr_catalog["status"] == -1:
                entry = {
                    "mentee": curr_catalog["mentee"],
                    "mentor": curr_mentor["email"],
                    "mentee_description": "N/A",
                    "mentor_description": curr_catalog["description"],
                    "hours": curr_catalog["hours"],
                    "date_confirmed": "N/A",
                    "date_met": curr_catalog["date"],
                }
                pairings.append(entry)

    return pairings
