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
from models.redismodel import (
    add_redis_collection_id,
    delete_redis_id,
    add_redis_collection,
)
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


router = APIRouter(tags=["club"])


class Club(BaseModel):
    advisor_email: str
    club_days: List[str]
    club_description: str
    club_name: str
    president_email: str
    room_number: int
    google_classroom_link: str
    secret_password: int
    start_time: str
    status: str
    vice_president_emails: List[str]


@router.post("/createclub/")
async def create_info(
    club: Club, username: Annotated[str, Depends(get_current_username)]
):
    try:
        # Client side makes sure that the president email and advisor emails are correct, etc.
        # Make club will make create it as Pending -> will wait for advisor verification to Approve it.
        make_club(
            club.advisor_email,
            club.club_days,
            club.club_description,
            club.club_name,
            club.president_email,
            club.room_number,
            club.google_classroom_link,
            club.secret_password,
            club.start_time,
            club.status,
            club.vice_president_emails,
        )

        club_id = get_el_id("Clubs", club.secret_password)
        coll_id = get_collection_id("Clubs", club_id)
        add_id = add_redis_collection_id("Clubs", coll_id, club_id=club_id)
        add_redis_collection("Users")

        # Now have to send email to advisor with password:
        receiver = club.advisor_email
        subject = f"CRLS Pathfinders | {club.club_name} Confirmation Code"
        body = f"""CODE: {club.secret_password}

{club.president_email} is registering their club on the CRLS PathFinders website, crlspathfinders.com.
To verify {club.club_name}, you can either email them your code, and they can verify themself, or you can log into the PathFinders website, select your email in the top right corner, hit "Verify Club," and then input the code above.
Once successful, {club.club_name} should appear after hitting "Find a Club."

Thank you, and if there are any problems, send me an email @25ranjaria@cpsd.us
"""
        try:
            send_mail(receiver, subject, body)
            print("Sent mail")
        except Exception as e:
            print(f"Failed to send mail: {e}")
            return {"status": f"Failed to send mail: {e}"}

        # Now send email to the club president:
        receiver = club.president_email
        subject = f"CRLS Pathfinders | {club.club_name} Confirmation Code"
        body = f"""Hello {club.president_email},

CONFIRMATION CODE: {club.secret_password}

We have recieved {club.club_name}'s registration.  
To verify {club.club_name}, log into crlspathfinders.com, select your email in the top right corner, hit "Verify Club," and then input the code above.
Once successful, {club.club_name} will appear after hitting "Find a Club." Try reloading the page if it's not there.

Thank you, and if there are any problems, send me an email @25ranjaria@cpsd.us
"""
        try:
            send_mail(receiver, subject, body)
            print("Sent mail")
        except Exception as e:
            print(f"Failed to send mail: {e}")
            return {"status": f"Failed to send mail: {e}"}
        return {"status": "Successfully created club"}
    except Exception as e:
        return {"status": f"Failed to create club: {e}"}


@router.post("/updateclub/")
async def update_club(
    club: Club, username: Annotated[str, Depends(get_current_username)]
):
    try:
        change_club(
            club.advisor_email,
            club.club_days,
            club.club_description,
            club.club_name,
            club.president_email,
            club.room_number,
            club.google_classroom_link,
            club.secret_password,
            club.start_time,
            club.status,
            club.vice_president_emails,
        )
        club_id = get_el_id("Clubs", club.secret_password)
        coll_id = get_collection_id("Clubs", club_id)
        add_id = add_redis_collection_id("Clubs", coll_id, club_id=club_id)
        if add_id["status"] == 0:
            return {"status": "Successfully edited club"}
        return {"status": f"Failed to update club redis: {add_id["error_message"]}"}
    except Exception as e:
        return {"status": f"Failed to edit club: {e}"}


class ChangeStatus(BaseModel):
    secret_password: int
    status: str


@router.post("/changestatus/")
def change_status(
    change_status: ChangeStatus, username: Annotated[str, Depends(get_current_username)]
):
    try:
        update_status(change_status.secret_password, change_status.status)
        club_id = get_el_id("Clubs", change_status.secret_password)
        coll_id = get_collection_id("Clubs", club_id)
        add_id = add_redis_collection_id("Clubs", coll_id, club_id=club_id)
        return {"status": "Successfully changed status"}
    except Exception as e:
        return {"status": f"Failed to change status: {e}"}


@router.get("/deleteclub/{club_id}")
def delete_club(club_id: str, username: Annotated[str, Depends(get_current_username)]):
    try:
        del_id = delete_redis_id("Clubs", club_id)
        if del_id["status"] == 0:
            remove_club(club_id)
            # Now remove this club from all of the users who are members of this club:
            # users = get_collection_python("Users")
            # print(f"57 - {users}")
            # for u in users:
            #     if len(u["joined_clubs"]) > 0:
            #         if club_id in u["joined_clubs"]:
            #             print("59 - Found!")
            #             join_leave_club("leave", u["email"], club_id)
            #         else:
            #             print("61 - Not found")
            return {"status": "Successfully deleted club"}
        return {"status": f"Failed to delete club redis: {del_id["error_message"]}"}

    except Exception as e:
        return {"status": f"Failed to delete club: {e}"}


class VerifyClub(BaseModel):
    secret_password: int


@router.post("/verifyclub")
def verify_club(
    verify: VerifyClub, username: Annotated[str, Depends(get_current_username)]
):
    try:
        status = verify_club_model(verify.secret_password)
        # print()
        return status
    except Exception as e:
        print(f"Club verification failed: {e}")
        return {"status": "Failed", "error": e}


@router.post("/uploadclubimage/")
async def upload_image(
    username: Annotated[str, Depends(get_current_username)],
    file: UploadFile = File(...),
    old_file_name: Optional[str] = Form(None),
):
    print(file)
    try:
        # Validate file type
        if file.content_type not in [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
        ]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPEG, JPG, PNG, WEBP, and GIF are allowed.",
            )
        if old_file_name:
            delete_club_image(old_file_name)

        img_url = upload_club_image(file)
        print(f"successfully uploaded club img: {img_url}")
        return {"status": img_url}
    except Exception as e:
        print(f"Failed: {e}")
        return {"status": "Failed"}


class SetClubImg(BaseModel):
    img_url: str
    club_id: str
    old_id: str


@router.post("/setclubimg/")
async def set_club_img(
    upload: SetClubImg, username: Annotated[str, Depends(get_current_username)]
):
    if upload.img_url != "Failed":
        set_club_image_doc(upload.club_id, upload.img_url, upload.old_id)
        coll_id = get_collection_id("Clubs", upload.club_id)
        add_id = add_redis_collection_id("Clubs", coll_id, club_id=upload.club_id)
        return {"status": "Successfully updated club img doc"}
    else:
        print("Failed to update club img doc.")
        return {"status": "Failed to update club img doc."}
