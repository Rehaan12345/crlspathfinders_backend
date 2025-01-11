from .model import db, get_el_id, get_doc, storage, get_collection_id
from .usermodel import change_user_role, join_leave_club, change_is_leader
from .mentormodel import extract_relative_path
from .redismodel import add_redis_collection_id
from fastapi import FastAPI, File, UploadFile, HTTPException
from uuid import uuid4
from io import BytesIO


def get_secret_pass(club_id):
    return db.collection("Clubs").document(club_id).get().to_dict()["secret_password"]


def make_club(
    advisor_email,
    club_days,
    club_description,
    club_name,
    president_email,
    room_number,
    google_classroom_link,
    secret_password,
    start_time,
    status,
    vice_presidents_emails,
):
    # Need to pass in the id, etc for which collection to actually change.
    collection = "Clubs"
    standard_img = "https://firebasestorage.googleapis.com/v0/b/crlspathfinders-82886.appspot.com/o/club-images%2Felementor-placeholder-image.webp?alt=media&token=ca920f5c-bcfa-4739-b6bc-12fd70b00c9c"
    try:
        db.collection(collection).add(
            {
                "advisor_email": advisor_email,
                "club_days": club_days,
                "club_description": club_description,
                "club_name": club_name,
                "president_email": president_email,
                "room_number": room_number,
                "google_classroom_link": google_classroom_link,
                "secret_password": secret_password,
                "start_time": start_time,
                "status": status,
                "vice_presidents_emails": vice_presidents_emails,
                "members": [],
                "club_img": standard_img,
                # Need to add img_url
            }
        )
        # Make the president and vice-presidents have "Leader" role and add club to joined_clubs:
        try:
            change_user_role(president_email, "Leader")
            print(f"Changed pres role: {president_email}")
            club_id = get_el_id("Clubs", secret_password)
            join_leave_club("join", president_email, club_id)
            print(f"pres joined {club_id}")
            members = get_members(club_id)
            members.append(president_email)
            print("added pres to club members")
            change_is_leader(president_email, True)
            print(f"changed {president_email} to is leader")
            for v in vice_presidents_emails:
                if len(v) > 1:
                    account = get_doc("Users", get_el_id("Users", v))
                    print(f"role: {account}")
                    if account["role"] == "Member":
                        change_user_role(v, "Leader")
                        print(f"changed vp role: {v}")
                    change_is_leader(v, True)
                    print(f"Changed {v} to is leader")
                    join_leave_club("join", v, club_id)
                    print(f"pres joined {club_id}")
                    members.append(v)
                    print("added vp to club members")
            manage_members(secret_password, members)
        except Exception as e:
            print(f"Failed to change pres / vp role: {e}")
        return {"status": "Success"}
    except Exception as e:
        print(f"Failed to make club: {e}")
        return {"status": f"Failed: {str(e)}"}


def change_club(
    advisor_email,
    club_days,
    club_description,
    club_name,
    president_email,
    room_number,
    google_classroom_link,
    secret_password,
    start_time,
    status,
    vice_presidents_emails,
):
    collection = "Clubs"
    doc_id = get_el_id(collection, secret_password)
    try:
        db.collection(collection).document(doc_id).update(
            {
                # Schema:
                "advisor_email": advisor_email,
                "club_days": club_days,
                "club_description": club_description,
                "club_name": club_name,
                "president_email": president_email,
                "room_number": room_number,
                "google_classroom_link": google_classroom_link,
                "secret_password": secret_password,
                "start_time": start_time,
                "status": status,
                "vice_presidents_emails": vice_presidents_emails,
            }
        )
        return {"status": "Success"}
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


def update_status(secret_password, status):
    collection = "Clubs"
    doc_id = get_el_id(collection, secret_password)
    try:
        db.collection(collection).document(doc_id).update({"status": status})
        return {"status": "Successfully changed status"}
    except Exception as e:
        return {"status": f"Failed to change status: {e}"}


def get_members(club_id):
    return db.collection("Clubs").document(club_id).get().to_dict()["members"]


def manage_members(secret_password, new_members):
    collection = "Clubs"
    doc_id = get_el_id(collection, secret_password)
    try:
        db.collection(collection).document(doc_id).update({"members": new_members})
        return {"status": "Successfully updated members"}
    except Exception as e:
        return {"status": f"Failed to update members: {e}"}


def remove_club(club_id):
    try:
        db.collection("Clubs").document(club_id).delete()
        # Also have to delete from joined club of every user, etc.
        return {"status": "Successfully deleted club"}
    except Exception as e:
        return {"status": f"Failed to delete club: {e}"}


def verify_club_model(secret_password):
    try:
        club_id = get_el_id("Clubs", secret_password)
        print(f"got id: {club_id}")
        whole_club = get_doc("Clubs", club_id)
        club = whole_club["club_name"]
        if whole_club["status"] == "Pending":
            update_status(secret_password, "Approved")
            club_id = get_el_id("Clubs", secret_password)
            coll_id = get_collection_id("Clubs", club_id)
            add_id = add_redis_collection_id("Clubs", coll_id, club_id=club_id)
            print(f"got club: {club}")
            return {"status": "Success", "club": club}
        elif whole_club["status"] == "Approved":
            return {"status": f"{club} is already approved!", "club": club}
    except Exception as e:
        print(f"Club verification failed: {e}")
        return {"status": "Failed", "error": e}


def upload_club_image(file: UploadFile = File(...)):
    try:
        # Generate a unique file name
        file_name = f"{uuid4()}.jpg"
        blob = storage.bucket().blob(f"club-images/{file_name}")

        # Upload the image
        blob.upload_from_file(file.file, content_type=file.content_type)
        blob.make_public()

        image_url = blob.public_url

        print(f"Successfully uploaded image: {image_url}")
        return image_url
    except Exception as e:
        print(f"Failed to upload img: {e}")
        return "Failed"


def delete_club_image(file_name):
    print(f"file_name: {file_name}")
    to_delete = "https://storage.googleapis.com/crlspathfinders-82886.appspot.com/"
    new_new_file_name = file_name[len(to_delete) :]
    # if file_path_or_url.startswith("http"):
    #     file_path_or_url = extract_relative_path(file_path_or_url)
    try:
        blob = storage.bucket().blob(new_new_file_name)
        blob.delete()
        print(f"Successfully deleted image: {file_name}")
    except Exception as e:
        print(f"Failed to delete image: {e}")


def set_club_image_doc(club_id, img_url, old_id):
    try:
        db.collection("Clubs").document(club_id).update({"club_img": img_url})
        delete_club_image(old_id)
        return {"status": "Successfully updated club img doc"}
    except Exception as e:
        print(f"Failed to update club img doc: {e}")
        return {"status": f"Failed to update club img doc: {e}"}
