from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from models.usermodel import make_user, change_user, verify_token, get_current_user, get_user_from_email, join_leave_club, change_user_role, delete_user, change_is_leader, change_is_mentor, change_mentor_eligible
from typing import Annotated, List
from models.model import get_el_id, get_doc
from models.clubmodel import get_members, manage_members, get_secret_pass

router = APIRouter(
    tags=["user"]
)

class User(BaseModel):
    email: str
    is_leader: bool
    role: str
    leading: List[str]
    joined_clubs: List[str]
    
@router.post("/createuser/")
async def create_user(user: User):
    return make_user(user.email, user.is_leader, user.role, user.leading, user.joined_clubs)

@router.post("/updateuser/")
async def update_user(user: User):
    return change_user(user.email, user.is_leader, user.password, user.role)

class Token(BaseModel):
    token: str

@router.post("/verify-token")
def verify_token_route(token: Token):
    decoded_token = verify_token(token.token)
    return {"uid": decoded_token["uid"], "email": decoded_token.get("email")}

@router.get("/protected")
def protected_route(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = auth_header.split("Bearer ")[-1]
    decoded_token = verify_token(token)
    return {"message": "You are authorized", "user_id": decoded_token["uid"]}

# New endpoint to handle additional user creation logic
@router.post("/create-user")
def create_user_route(token: Token):
    # Creates / adds the user into the Google Firebase Authentication:
    decoded_token = verify_token(token.token)
    # Creates / adds the user into the Google Firebase Firestore Database:
    # user = User()
    print(f"successfully created user: {decoded_token['uid']}")
    return {"status": "User created successfully", "user_id": decoded_token["uid"]}

@router.post("/make-user")
def make_new_user(user: User):
    try:
        make_user(user.email, user.is_leader, user.role, user.leading, user.joined_clubs)
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
def get_user_doc_data(email: str):
    print("starting getuserdocdata")
    try:
        return get_user_from_email(email)
    except Exception as e:
        return {"status": f"Faield to getuserdocfromdata: {e}"}
    
@router.get("/toggleclub/{email}/{club_id}")
def toggle_club(email: str, club_id: str):
    user = get_user_from_email(email)
    clubs = user["joined_clubs"]
    # print(clubs)

    members = get_members(club_id)
    secret_password = get_secret_pass(club_id)

    if club_id in clubs:
        try:
            join_leave_club("leave", email, club_id)
            members.remove(email)
            manage_members(secret_password, members)
            return {"status": "Successfully left club"}
        except Exception as e:
            return {"status": f"Failed to leave club: {e}"}
    else:
        try:
            join_leave_club("join", email, club_id)
            members.append(email)
            manage_members(secret_password, members)
            return {"status": "Successfully joined club"}
        except Exception as e:
            return {"status": f"Failed to leave club: {e}"}

class ChangeRole(BaseModel):
    email: str
    new_role: str

@router.post("/changerole")
def change_role(change: ChangeRole):
    try:
        change_user_role(change.email, change.new_role)
        return {"status": "Successfully changed user role"}
    except Exception as e:
        print(f"Failed to change role: {e}")
        return {"status": f"Failed to change user role: {e}"}
    
@router.get("/deleteuser/{email}")
def remove_user(email: str):
    try:
        delete_user(email)
        return {"status": "Successfully deleted user"}
    except Exception as e:
        print(f"Failed to change role: {e}")
        return {"status": f"Failed to delete user: {e}"}

class ToggleLeaderMentor(BaseModel):
    email: str
    leader_mentor: str
    toggle: bool

@router.post("/toggleleadermentor")
def toggle_leader_mentor(toggle: ToggleLeaderMentor):
    if toggle.leader_mentor == "Leader":
        try:
            change_is_leader(toggle.email, toggle.toggle)
            print(f"Changed {toggle.email} to {toggle.toggle}")
            return {"status": "Successfully toggled leader"}
        except Exception as e:
            print(f"Failed to toggle leader: {e}")
            return {"status": f"Failed to toggle leader: {e}"}
    if toggle.leader_mentor == "Mentor":
        try:
            change_is_mentor(toggle.email, toggle.toggle)
            print(f"Changed {toggle.email} to {toggle.toggle}")
            return {"status": "Successfully toggled mentor"}
        except Exception as e:
            print(f"Failed to toggle mentor: {e}")
            return {"status": f"Failed to toggle mentor: {e}"}
    if toggle.leader_mentor == "Mentor-Eligible":
        try:
            change_mentor_eligible(toggle.email, toggle.toggle)
            print(f"Changed {toggle.email} to {toggle.toggle}")
            return {"status": "Successfully toggled mentor eligible"}
        except Exception as e:
            print(f"Failed to toggle mentor eligible: {e}")
            return {"status": f"Failed to toggle mentor eligible: {e}"}
    print(f"Wrong / not enough parameters in toggle leader mentor ok.")
    return {"status": "Incorrect parameters"}