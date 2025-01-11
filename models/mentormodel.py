from .model import db, get_el_id, get_doc, storage, get_collection_id
from .usermodel import change_user_role, change_is_mentor
from .redismodel import add_redis_collection_id
from fastapi import FastAPI, File, UploadFile, HTTPException
from uuid import uuid4
from io import BytesIO
import uuid
from urllib.parse import urlparse


def make_mentor(
    firstname, lastname, bio, email, race, religion, gender, languages, academics
):
    # Need to pass in the id, etc for which collection to actually change.
    collection = "Mentors"
    print("make mentor begin")
    try:
        result = db.collection(collection).add(
            {
                "firstname": firstname,
                "lastname": lastname,
                "bio": bio,
                "email": email,
                "races": race,
                "religions": religion,
                "gender": gender,
                "languages": languages,
                "academics": academics,
                "profile_pic": "",
                "show": True,
                "total_hours_worked": 0,
                "hours_worked_catalog": [],
            }
        )
        print(result)
        mentor_role = get_doc("Users", get_el_id("Users", email))["role"]
        print(f"Mentor role: {mentor_role}")
        if mentor_role == "Member":
            change_user_role(email, "Mentor")
            print(f"changed {email} role to mentor")
        change_is_mentor(email, True)
        print(f"changed {email} is mentor")
        return {"status": "Success"}
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


def change_mentor(
    firstname, lastname, bio, email, race, religion, gender, languages, academics
):
    collection = "Mentors"
    doc_id = get_el_id("Mentors", email)
    try:
        result = (
            db.collection(collection)
            .document(doc_id)
            .update(
                {
                    "firstname": firstname,
                    "lastname": lastname,
                    "bio": bio,
                    "email": email,
                    "races": race,
                    "religions": religion,
                    "gender": gender,
                    "languages": languages,
                    "academics": academics,
                    # Need to add img_url
                }
            )
        )
        return {"status": "Success"}
    except Exception as e:
        return {"status": f"Failed: {str(e)}"}


def remove_mentor(email):
    doc_id = get_el_id("Mentors", email)
    try:
        db.collection("Mentors").document(doc_id).delete()
        return {"Status": "Successfully deleted mentor"}
    except Exception as e:
        return {"status": f"Failed to delete mentor: {e}"}


# Make function that deletes old mentor image (look on google or chatgpt how to delte firebase storage images from a url)


def upload_mentor_image(file: UploadFile = File(...)):
    try:
        # Generate a unique file name
        file_name = f"{uuid4()}.jpg"
        blob = storage.bucket().blob(f"mentor-images/{file_name}")

        # Upload the image
        blob.upload_from_file(file.file, content_type=file.content_type)
        blob.make_public()

        image_url = blob.public_url

        print(f"Successfully uploaded image: {image_url}")
        return image_url
    except Exception as e:
        print(f"Failed to upload img: {e}")
        return "Failed"


def extract_relative_path(full_url):
    """
    Extract the relative path from the full Firebase Storage URL.
    """
    parsed_url = urlparse(full_url)
    # Firebase Storage URL paths start with '/v0/b/{bucket}/o/{path}', so we extract 'path'
    path = (
        parsed_url.path.split("/o/")[-1]
        if "/o/" in parsed_url.path
        else parsed_url.path
    )
    return path.replace("%2F", "/")  # Decode URL-encoded slashes


def delete_mentor_image(file_name):
    print(f"file_name: {file_name}")
    new_file_name = extract_relative_path(file_name)
    to_delete = "https://storage.googleapis.com/crlspathfinders-82886.appspot.com/"
    new_new_file_name = file_name[len(to_delete) :]
    print(f"new_new_file_name: {new_new_file_name}")
    print(f"new_file_name: {new_file_name}")
    # if file_path_or_url.startswith("http"):
    #     file_path_or_url = extract_relative_path(file_path_or_url)
    try:
        blob = storage.bucket().blob(new_new_file_name)
        print(blob)
        blob.delete()
        print(f"Successfully deleted image: {file_name}")
    except Exception as e:
        print(f"Failed to delete image: {e}")


def set_mentor_image_doc(mentor_email, img_url):
    mentor_id = get_el_id("Mentors", mentor_email)
    print(f"mentor id: {mentor_id}, email: {mentor_email}")
    try:
        db.collection("Mentors").document(mentor_id).update({"profile_pic": img_url})
        return {"status": "Successfully updated mentor img doc"}
    except Exception as e:
        print(f"Failed to update mentor img doc: {e}")
        return {"status": f"Failed to update mentor img doc: {e}"}


def show_or_hide_mentor(mentor_email):
    doc_id = get_el_id("Mentors", mentor_email)
    mentor = get_doc("Mentors", doc_id)
    toggle = not mentor["show"]
    # print(not toggle)
    try:
        db.collection("Mentors").document(doc_id).update({"show": toggle})
        mentor_id = get_el_id("Mentors", mentor.email)
        coll_id = get_collection_id("Mentors", mentor_id)
        add_id = add_redis_collection_id("Mentors", coll_id, mentor_id=mentor_id)
    except Exception as e:
        print(f"Failed to show or hide mentor: {e}")
        return {"status": f"Failed to show or hide mentor: {e}"}


def update_mentor_hours(mentor_email, hours):
    # hours could be a negative number as well to reduce the total_hours_worked amount.
    doc_id = get_el_id("Mentors", mentor_email)
    mentor = get_doc("Mentors", doc_id)
    curr_hours = mentor["total_hours_worked"]
    new_hours = int(curr_hours) + int(hours)
    try:
        db.collection("Mentors").document(doc_id).update(
            {"total_hours_worked": new_hours}
        )
        return {"status": "Success"}
    except Exception as e:
        print(f"Failed to update mentor hours: {e}")
        return {"status": f"Failed to update mentor hours: {e}"}


def update_hours_worked_catalog(
    catalog_id, mentor_email, mentee_email, description, hours_worked, date, status
):
    new_catalog = {
        "id": catalog_id,
        "mentee": mentee_email,
        "description": description,
        "hours": hours_worked,
        "date": str(date),
        "status": status,
    }
    doc_id = get_el_id("Mentors", mentor_email)
    mentor = get_doc("Mentors", doc_id)
    whole_catalog = mentor["hours_worked_catalog"]
    whole_catalog.append(new_catalog)
    try:
        db.collection("Mentors").document(doc_id).update(
            {"hours_worked_catalog": whole_catalog}
        )
        return {"status": "Success"}
    except Exception as e:
        print(f"Failed to update mentor hours: {e}")
        return {"status": f"Failed to update mentor hours: {e}"}


def confirm_mentor_mentee_logging(catalog_id, mentee_email, mentor_email, mentee_hours):
    mentor_id = get_el_id("Mentors", mentor_email)
    mentor = get_doc("Mentors", mentor_id)
    # mentee = get_doc("Users", mentee_id)
    # Update mentor catalog with confirmed status
    try:
        catalog = mentor["hours_worked_catalog"]
        print(catalog)
        for h in catalog:
            print(h)
            if h["id"] == catalog_id and h["mentee"] == mentee_email:
                print("catalog found")
                if h["status"] == 0:  # This has already been changed, so skip
                    return {
                        "status": -1,
                        "error_message": "This log has already been confirmed.",
                    }
                if h["hours"] == str(mentee_hours):
                    print("found correct catalog with correct hours")
                    curr_catalog = h
                    curr_catalog["status"] = 0
                    catalog[catalog.index(h)] = curr_catalog
                    db.collection("Mentors").document(mentor_id).update(
                        {"hours_worked_catalog": catalog}
                    )
                    print("updated collection")
                    # Only updates the mentor hours once the mentee has confirmed.
                    update_mentor_hours(mentor_email, mentee_hours)
                    print("updated mentor hours")
                    return {"status": 0, "mentor_log": h}
                else:
                    print("mismatching hours reported")
                    return {
                        "status": -2,
                        "error_message": "Mismatching hours reported.",
                    }
        return {"status": -1, "error_message": "No matching catalog id found"}
    except Exception as e:
        return {"status": -1, "error_message": e}


def get_mentor_description(mentor_email, target_catalog_id):
    mentor_id = get_el_id("Mentors", mentor_email)
    mentor = get_doc("Mentors", mentor_id)
    catalog = mentor["hours_worked_catalog"]

    for c in catalog:
        if c["id"] == target_catalog_id:
            return {"status": 0, "desc": c["description"]}

    return {"status": -1, "error_message": "No matching catalog found"}
