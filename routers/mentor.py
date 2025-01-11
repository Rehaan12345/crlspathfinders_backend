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
import secrets
from pydantic import BaseModel
from typing import List, Optional, Annotated
from models.mentormodel import (
    make_mentor,
    change_mentor,
    remove_mentor,
    upload_mentor_image,
    set_mentor_image_doc,
    show_or_hide_mentor,
    update_mentor_hours,
    update_hours_worked_catalog,
    confirm_mentor_mentee_logging,
    delete_mentor_image,
    get_mentor_description,
)
from models.usermodel import update_mentee_catalog
from models.model import get_el_id, get_collection_id
from models.redismodel import add_redis_collection_id, delete_redis_id
from sendmail import send_mail
import uuid, os, datetime
from dotenv import load_dotenv

load_dotenv()
curr_url = os.environ.get("CURR_URL")

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


router = APIRouter(tags=["mentor"])


class Mentor(BaseModel):
    firstname: str
    lastname: str
    bio: str
    email: str
    races: List[str]
    religions: List[str]
    gender: List[str]  # Change to just a string later
    languages: List[str]
    academics: List[str]


@router.post("/creatementor/")
async def create_mentor(
    mentor: Mentor, username: Annotated[str, Depends(get_current_username)]
):
    try:
        print("create mentor start")
        make_mentor(
            mentor.firstname,
            mentor.lastname,
            mentor.bio,
            mentor.email,
            mentor.races,
            mentor.religions,
            mentor.gender,
            mentor.languages,
            mentor.academics,
        )
        mentor_id = get_el_id("Mentors", mentor.email)
        coll_id = get_collection_id("Mentors", mentor_id)
        add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
        print(add_id)
        if add_id["status"] == 0:
            return {"status": "Successfully edited mentor"}
        return {"status": f"Failed to update mentor redis: {add_id["error_message"]}"}
    except Exception as e:
        return {"status": f"Failed to create mentor: {e}"}


@router.post("/updatementor/")
async def update_mentor(
    mentor: Mentor, username: Annotated[str, Depends(get_current_username)]
):
    try:
        change_mentor(
            mentor.firstname,
            mentor.lastname,
            mentor.bio,
            mentor.email,
            mentor.races,
            mentor.religions,
            mentor.gender,
            mentor.languages,
            mentor.academics,
        )
        mentor_id = get_el_id("Mentors", mentor.email)
        coll_id = get_collection_id("Mentors", mentor_id)
        add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
        if add_id["status"] == 0:
            return {"status": "Successfully edited mentor"}
    except Exception as e:
        return {"status": f"Failed to edit mentor: {e}"}


@router.get("/deletementor/{email}")
async def delete_mentor(
    email: str, username: Annotated[str, Depends(get_current_username)]
):
    try:
        mentor_id = get_el_id("Mentors", email)
        del_id = delete_redis_id("Mentors", mentor_id)
        if del_id["status"] == 0:
            remove_mentor(email)
            return {"Status": "Successfully deleted mentor"}
        return {"status": f"Failed to delete pml redis: {del_id["error_message"]}"}
    except Exception as e:
        return {"status": f"Failed to delete mentor: {e}"}


# Make router that accepts deleted image and calls the function to delete the image in mentormodel.py
"""
@router.get("/deleteimage/{old_url})
def delete_img(old_url: str):
    return handle_delete_img(old_url)
"""
# Something like that^


@router.post("/uploadmentorimage/")
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
            delete_mentor_image(old_file_name)

        img_url = upload_mentor_image(file)
        print(f"successfully uploaded mentor img: {img_url}")
        return {"status": img_url}
    except Exception as e:
        print(f"Failed: {e}")
        return {"status": "Failed"}


class SetClubImg(BaseModel):
    img_url: str
    mentor_email: str


@router.post("/setmentorimg/")
async def set_club_img(
    upload: SetClubImg, username: Annotated[str, Depends(get_current_username)]
):
    if upload.img_url != "Failed":
        set_mentor_image_doc(upload.mentor_email, upload.img_url)
        mentor_id = get_el_id("Mentors", upload.mentor_email)
        coll_id = get_collection_id("Mentors", mentor_id)
        add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
        return {"status": "Successfully updated mentor img doc"}
    else:
        print("Failed to update mentor img doc.")
        return {"status": "Failed to update mentor img doc."}


class MentorPitch(BaseModel):
    mentor_email: str
    pitch: str


@router.post("/sendmentorpitch/")
async def send_mentor_pitch(
    mentor_pitch: MentorPitch, username: Annotated[str, Depends(get_current_username)]
):
    receiver = "crlspathfinders25@gmail.com"
    subject = f"Mentor pitch from {mentor_pitch.mentor_email}"
    body = f"""Mentor pitch received from {mentor_pitch.mentor_email}

Pitch:
{mentor_pitch.pitch}
    """
    try:
        send_mail(receiver, subject, body)
        print("Sent mentor pitch mail")
        return {"status": "Sent mentor pitch mail"}
    except Exception as e:
        print(f"Failed to send mentor pitch email: {e}")
        return {"status": f"Failed to send mentor pitch email: {e}"}


class MentorMenteeLog(BaseModel):
    mentor_email: str
    mentee_email: str
    log_description: str
    log_hours: str


@router.post("/mentormenteelogs/")
def log_mentor_mentee(
    log: MentorMenteeLog, username: Annotated[str, Depends(get_current_username)]
):
    print("started mentormentee logs")
    # Send crlspathfinders25 the log, send mentor the confirmation, and send mentee the confirmation.
    try:

        catalog_id = str(uuid.uuid4())

        # Send to crlspathfinders25:
        receiver = "crlspathfinders25@gmail.com"
        subject = f"Mentor-Mentee Logging Form from {log.mentor_email}"
        body = f"""{log.mentor_email} has submitted a logging form.

Description: {log.log_description}

Hours: {log.log_hours}
"""
        send_mail(receiver, subject, body)
        print("sent cp email")

        # Send email to mentor:
        receiver = log.mentor_email
        subject = "Confirmation of Mentor-Mentee Logging Form"
        body = f"""Hello,

You have successfully logged your hours. The CRLS PathFinders team has recieved your hours, and a confirmation email has been sent to your mentee, {log.mentee_email}. Once they have confirmed that the hours are correct, your hours will be logged and you can receieve community service hours for your work.
Below are your responses. To change anything, please send an email to crlspathfinders25@gmail.com or just fill out a new form.
Mentee: {log.mentee_email}

Description: {log.log_description}

Hours: {log.log_hours}

Thank you,
CRLS PathFinders,
Rehaan Anjaria '25
Abel Asefaw '25
"""
        send_mail(receiver, subject, body)
        print("sent mentor email")

        # Update mentor total_hours_worked
        # try:
        #     update_mentor_hours(log.mentor_email, log.log_hours)
        #     print("Successfully updated mentor hours")
        # except Exception as e:
        #     print(f"Failed to update mentor hours: {e}")

        # Update catalog data:
        try:
            date = datetime.date.today()
            status = -1  # -1 means mentee not confirmed, 0 means mentee confirmed.
            update_hours_worked_catalog(
                catalog_id,
                log.mentor_email,
                log.mentee_email,
                log.log_description,
                log.log_hours,
                date,
                status,
            )
            mentor_id = get_el_id("Mentors", log.mentor_email)
            coll_id = get_collection_id("Mentors", mentor_id)
            add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
            print("Successfully updated mentor hours")
        except Exception as e:
            print(f"Failed to update mentor catalog: {e}")

        # Send email to mentee:
        receiver = log.mentee_email
        subject = f"Mentor-Mentee Logging Form from {log.mentor_email}"
        body = f"""Hello,

Your mentor, {log.mentor_email}, has submitted a logging form. If they are not your mentor, please ignore this message.

Please confirm that the below hours are correct. If you have any questions please reach out to your mentor at {log.mentor_email} or email us with any questions at crlspathfinders25@gmail.com

Hours: {log.log_hours}

To confirm that you and your mentor, {log.mentor_email}, have worked {log.log_hours} hours, please go to crlspathfinders.com/confirmmenteehours/{int(-1)}/{catalog_id}/{log.mentee_email}/{log.mentor_email}/{log.log_hours}/NoDescription/

Thank you,
CRLS PathFinders,
Rehaan Anjaria '25
Abel Asefaw '25
"""

        send_mail(receiver, subject, body)
        print("sent mentee email")
        return {"status": "Successfully send logging email"}
    except Exception as e:
        print(f"Failed to send logging email: {e}")
        return {"status": f"Failed to send logging email: {e}"}


@router.get("/toggleshowmentor/{mentor_email}/")
def toggle_show_mentor(
    mentor_email: str, username: Annotated[str, Depends(get_current_username)]
):
    return show_or_hide_mentor(mentor_email)


class MenteeConfirmHours(BaseModel):
    confirm: int
    catalog_id: str
    mentee_email: str
    mentor_email: str
    mentee_hours: str
    mentee_description: str


@router.post("/menteeconfirmhours/")
def mentee_confirm_hours(
    mentee_log: MenteeConfirmHours,
    username: Annotated[str, Depends(get_current_username)],
):
    confirm = mentee_log.confirm
    catalog_id = mentee_log.catalog_id
    mentee_email = mentee_log.mentee_email
    mentor_email = mentee_log.mentor_email
    mentee_hours = mentee_log.mentee_hours
    mentee_description = mentee_log.mentee_description
    print(mentee_log)
    # First check if confirm is True
    # If true, first change mentee is_mentor to True, and update their mentee logs with their own description, timestamp, hours worked, and with which mentor they worked.
    # Then, update mentor logs.
    if confirm == 0:  # 0 = yes, -1 = no
        log_status = confirm_mentor_mentee_logging(
            catalog_id, mentee_email, mentor_email, mentee_hours
        )
        if log_status["status"] == 0:
            mentor_id = get_el_id("Mentors", mentee_log.mentor_email)
            coll_id = get_collection_id("Mentors", mentor_id)
            add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
            print(add_id)
            # do the mentee logging
            print("mentor log found")
            mentor_log = log_status["mentor_log"]
            date_met = mentor_log["date"]
            date_confirmed = datetime.date.today()
            update_mentee_catalog(
                catalog_id,
                mentee_email,
                mentor_email,
                mentee_hours,
                mentee_description,
                str(date_confirmed),
                date_met,
            )
            mentor_id = get_el_id("Mentors", mentee_log.mentor_email)
            coll_id = get_collection_id("Mentors", mentor_id)
            add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
            print(add_id)
        elif log_status["status"] == -2:  # Mismatching hours:
            print("hours do not match confirmed")
            return {"status": -2, "error_message": "Hours do not match."}
        else:
            print(
                f"Failed to confirm mentor mentee logging: {log_status["error_message"]}"
            )
            return {
                "status": -1,
                "error_message": f"Failed to confirm mentor mentee logging: {log_status["error_message"]}",
            }

        # If go to here, that means all has worked. Now send confirmation email to crlspathfinders25@gmail.com:
        receiver = "crlspathfinders25@gmail.com"
        subject = f"{mentee_email} Confirmation Successful"
        mentor_description = get_mentor_description(mentor_email, catalog_id)
        if mentor_description["status"] == -1:
            return {
                "status": -1,
                "error_message": "Matching mentor description could not be found. Contact support.",
            }
        mentor_description = mentor_description["desc"]
        body = f"""As of {date_confirmed}, {mentee_email} has confirmed {mentor_email}'s hours log of {mentee_hours}.

Mentee Description: {mentee_description}
Mentor Description: {mentor_description}
"""
        send_mail(receiver, subject, body)

        # Send confirmation email to mentor:
        n_receiver = mentor_email
        n_subject = f"{mentee_email} Mentee Confirmation Successful"
        n_body = f"""Hello,

{mentee_email} has confirmed that you have worked {mentee_hours} hours together on {date_met}.
You can now go back to crlspathfinders.com/findamentor and click on "Log Mentor Hours" to see your completed hours.

Let us know if there are any problems,
CRLS PathFinders,
Rehaan Anjaria '25
Abel Asefaw '25
"""
        print(n_receiver)
        print(n_subject)
        print(n_body)
        send_mail(n_receiver, n_subject, n_body)

        mentor_id = get_el_id("Mentors", mentee_log.mentor_email)
        coll_id = get_collection_id("Mentors", mentor_id)
        add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
        print(add_id)

        return {"status": 0}
    return {"status": -1, "error_message": "confirm came back false (0)"}
