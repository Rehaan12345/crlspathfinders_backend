from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from models.clubmodel import make_club, change_club, update_status, remove_club
from models.model import get_collection_python
from models.usermodel import join_leave_club

router = APIRouter(
    tags=["club"]
)

class Club(BaseModel):
    advisor_email: str
    club_days: List[str]
    club_description: str
    club_name: str
    president_email: str
    room_number: int
    secret_password: int
    start_time: str
    status: str
    vice_president_emails: List[str]

@router.post("/createclub/")
async def create_info(club: Club):
    try:
        make_club(club.advisor_email, club.club_days, club.club_description, club.club_name, club.president_email, club.room_number, club.secret_password, club.start_time, club.status, club.vice_president_emails)
        return {"status": "Successfully created club"}
    except Exception as e:
        return {"status": f"Failed to create club: {e}"}

@router.post("/updateclub/")
async def update_club(club: Club):
    try:
        change_club(club.advisor_email, club.club_days, club.club_description, club.club_name, club.president_email, club.room_number, club.secret_password, club.start_time, club.status, club.vice_president_emails)
        return {"status": "Successfully edited club"}
    except Exception as e:
        return {"status": f"Failed to edit club: {e}"}

class ChangeStatus(BaseModel):
    secret_password: int
    status: str

@router.post("/changestatus/")
def change_status(change_status: ChangeStatus):
    try:
        update_status(change_status.secret_password, change_status.status)
        return {"status": "Successfully changed status"}
    except Exception as e:
        return {"status": f"Failed to change status: {e}"}
    
@router.get("/deleteclub/{club_id}")
def delete_club(club_id: str):
    try:
        remove_club(club_id)
        # Now remove this club from all of the users who are members of this club:
        users = get_collection_python("Users")
        print(f"57 - {users}")
        for u in users:
            if len(u["joined_clubs"]) > 0:
                if club_id in u["joined_clubs"]:
                    print("59 - Found!")
                    join_leave_club("leave", u["email"], club_id)
                else: print("61 - Not found")
        return {"status": "Successfully deleted club"}
    except Exception as e:
        return {"status": f"Failed to delete club: {e}"}