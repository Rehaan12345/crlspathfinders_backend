from .model import (
    db,
    get_el_id,
    get_doc,
    storage,
    get_collection_id,
    get_collection_python,
)
from .usermodel import change_user_role, change_is_mentor
from fastapi import FastAPI, File, UploadFile, HTTPException
from uuid import uuid4
from io import BytesIO


def create_link(link_name, link_url, categories, bio, deadline):
    collection = "PeerMentorLinks"
    print("make peermentorlink begin")
    try:
        db.collection(collection).add(
            {
                "name": link_name,
                "src": link_url,
                "categories": categories,
                "bio": bio,
                "deadline": deadline,
            }
        )
        return {"status": "Success"}
    except Exception as e:
        print(f"Failed to create pml link: {e}")
        return {"status": f"Failed: {str(e)}"}


def remove_link(name):
    doc_id = get_el_id("PeerMentorLinks", name)
    print(f"link_id: {doc_id}")
    try:
        db.collection("PeerMentorLinks").document(doc_id).delete()
        print(f"removed link: {doc_id}")
        return {"Status": "Successfully removed link"}
    except Exception as e:
        print(f"Failed to delete link: {e}")
        return {"status": f"Failed to remove link: {e}"}


def update_link(oldname, newname, newurl, categories, bio, deadline):
    print(categories)
    collection = "PeerMentorLinks"
    try:
        doc_id = get_el_id(collection, oldname)
        print(doc_id)
    except Exception as e:
        print(f"Failed to find doc_id: {e}")
    try:
        db.collection(collection).document(doc_id).update(
            {
                "name": newname,
                "src": newurl,
                "categories": categories,
                "bio": bio,
                "deadline": deadline,
            }
        )
        return {"status": "Successfully updated link"}
    except Exception as e:
        print(f"Failed to update link: {str(e)}")
        return {"status": f"Failed: {str(e)}"}


def update_category(old_cat_name, new_cat_name):
    collection = "Demographics"
    doc_id = "PeerMentor"
    all_cats = get_collection_id(collection, doc_id)["categories"]
    print(all_cats)
    for i in all_cats:
        if i == old_cat_name:
            all_cats[all_cats.index(i)] = new_cat_name

    try:
        db.collection(collection).document(doc_id).update({"categories": all_cats})
        print("Successfully edited category")
        return {"status": "Successfully edited category"}
    except Exception as e:
        print(f"Failed to edit category: {e}")
        return {"status": f"Failed to edit category: {e}"}


def create_category(cat_name):
    collection = "Demographics"
    doc_id = "PeerMentor"
    all_cats = get_collection_id(collection, doc_id)["categories"]
    all_cats.append(cat_name)
    try:
        db.collection(collection).document(doc_id).update({"categories": all_cats})
        print("Successfully created category")
        return {"status": "Successfully created category"}
    except Exception as e:
        print(f"Failed to create category: {e}")
        return {"status": f"Failed to create category: {e}"}


def delete_category(cat_name):
    collection = "Demographics"
    doc_id = "PeerMentor"
    all_cats = get_collection_id(collection, doc_id)["categories"]
    all_cats.remove(cat_name)
    try:
        db.collection(collection).document(doc_id).update({"categories": all_cats})
        print("Successfully deleted category")
        # When deleting category, also have to remove this category from all of the peer mentor links who have this category listed:
        pml = get_collection_python("PeerMentorLinks")
        for p in pml:
            if cat_name in p["categories"]:
                curr_cats = p["categories"]
                curr_cats.remove(cat_name)
                db.collection("PeerMentorLinks").document(p["id"]).update(
                    {"categories": curr_cats}
                )
        return {"status": "Successfully deleted category"}
    except Exception as e:
        print(f"Failed to delete category: {e}")
        return {"status": f"Failed to delete category: {e}"}
