from .model import db, get_el_id, get_doc, get_collection_python
from fastapi import HTTPException, Header, Depends
from firebase_admin import auth
from sendmail import send_mail
from .redismodel import redis, get_redis_collection_id


def make_user(email, is_leader, role, leading, joined_clubs):
    collection = "Users"
    try:
        curr_year = email[:2]
        curr_grade = "Teacher"
        if curr_year == "25":
            curr_grade = "Senior"
        elif curr_year == "26":
            curr_grade = "Junior"
        elif curr_year == "27":
            curr_grade = "Sophomore"
        elif curr_year == "28":
            curr_grade = "Freshman"
        result = db.collection(collection).add(
            {
                "email": email,
                "is_leader": is_leader,
                "role": role,
                "leading": leading,
                "joined_clubs": joined_clubs,
                "is_mentor": False,
                "is_mentee": False,
                "mentee_logs": [],
                "grade": curr_grade,
                # Need to add img_url
            }
        )
        print(result)
        # Send email when new user signs up
        receiver = "crlspathfinders25@gmail.com"
        subject = "New user login"
        body = f"""{email} just made an account.
"""
        send_mail(receiver, subject, body)
        return {"status": "Success"}
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


def change_user(email, is_leader, password, role):
    collection = "Users"
    doc_id = get_el_id("Users", email)
    try:
        result = (
            db.collection(collection)
            .document(doc_id)
            .update(
                {
                    # Schema:
                    "email": email,
                    "is_leader": is_leader,
                    "password": password,
                    "role": role,
                }
            )
        )
        print(result)
        return {"status": "Success"}
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


# Google Firebase Authentication implementation:
def verify_token(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


def get_current_user(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_user_from_email(email):
    collection = "Users"
    try:
        doc_id = get_el_id("Users", email)
        # user = db.collection(collection).document(doc_id).get().to_dict()
        user = get_redis_collection_id("Users", doc_id)
        print(user)
        if user["status"] == 0:
            return user["target_val"]
    except Exception as e:
        return f"Failed to getuserfromemail: {e}"


def join_leave_club(join_leave, email, club):
    try:
        user = get_user_from_email(email)
        user_id = get_el_id("Users", email)
        print(user_id)
        clubs = user["joined_clubs"]
        print(clubs)

        if join_leave == "leave":
            clubs.remove(club)
        elif join_leave == "join":
            clubs.append(club)

        doc = db.collection("Users").document(user_id)
        doc.update({"joined_clubs": clubs})
        return {"status": "Successfully left club"}
    except Exception as e:
        return {"status": f"Failed to leave club: {e}"}


def change_user_role(email, role):
    try:
        user_id = get_el_id("Users", email)
        print(f"userid - {user_id}")
        curr_role = get_doc("Users", user_id)["role"]
        if curr_role == "Mentor" and role == "Member":
            change_is_mentor(email, False)
        elif curr_role == "Member" and role == "Mentor":
            change_is_mentor(email, True)
        elif curr_role == "Leader" and role == "Member":
            change_is_leader(email, False)
        elif curr_role == "Member" and role == "Leader":
            change_is_leader(email, True)
        doc = db.collection("Users").document(user_id)
        doc.update({"role": role})
        return {"status": "Successfully changed user role"}
    except Exception as e:
        print(f"Failed to change role: {e}")
        return {"status": f"Failed to change user role: {e}"}


def delete_user(email):
    try:
        print("starting user delete")
        # Delete user from Firebase auth:
        user_record = auth.get_user_by_email(email)
        print(f"user record: {user_record}")
        user_id = user_record.uid
        print(f"User ID from Firebase Auth - {user_id}")
        # Delete the user from Firebase Authentication
        auth.delete_user(user_id)
        print(f"User successfully deleted from Firebase Authentication")
        user_id = get_el_id("Users", email)
        print(f"userid - {user_id}")
        db.collection("Users").document(user_id).delete()
        return {"status": "Successfully deleted user"}
    except Exception as e:
        print(f"Failed to delete user: {e}")
        return {"status": f"Failed to delete user: {e}"}


def change_is_leader(email, leader):
    try:
        user_id = get_el_id("Users", email)
        db.collection("Users").document(user_id).update({"is_leader": leader})
        return {"status": "Successfully changed is leader"}
    except Exception as e:
        print(f"Failed to change is leader: {e}")
        return {"status": f"Failed to change is leader: {e}"}


def change_is_mentor(email, mentor):
    try:
        user_id = get_el_id("Users", email)
        db.collection("Users").document(user_id).update({"is_mentor": mentor})
        return {"status": "Successfully changed is mentor"}
    except Exception as e:
        print(f"Failed to change is mentor: {e}")
        return {"status": f"Failed to change is mentor: {e}"}


def change_mentor_eligible(email, eligible):
    try:
        user_id = get_el_id("Users", email)
        db.collection("Users").document(user_id).update({"mentor_eligible": eligible})
        return {"status": "Successfully changed mentor eligible"}
    except Exception as e:
        print(f"Failed to change mentor eligible: {e}")
        return {"status": f"Failed to change mentor eligible: {e}"}


def update_mentee_catalog(
    catalog_id,
    mentee_email,
    mentor_email,
    hours,
    mentee_description,
    date_confirmed,
    date_met,
):
    new_mentee_catalog = {
        "id": catalog_id,  # Same id as the mentor catalog's id
        "mentor": mentor_email,
        "hours": hours,
        "description": mentee_description,
        "date_confirmed": date_confirmed,
        "date_met": date_met,
    }
    mentee_id = get_el_id("Users", mentee_email)
    mentee = get_doc("Users", mentee_id)
    mentee_logs = mentee["mentee_logs"]
    # Plan for outliers - only append if the id is unique.
    for m in mentee_logs:
        if m["id"] == new_mentee_catalog["id"]:
            return -1
    mentee_logs.append(new_mentee_catalog)
    db.collection("Users").document(mentee_id).update(
        {"is_mentee": True, "mentee_logs": mentee_logs}
    )


def get_mentees():
    all_users = get_collection_python("Users")
    mentees = []
    for u in all_users:
        if u["is_mentee"]:
            mentees.append(u)
    return mentees
