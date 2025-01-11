from .model import (
    db,
    get_el_id,
    get_doc,
    storage,
    get_collection_id,
    get_collection_python,
)


def update_all_info_collection(doc, vals):  # vals is a dict
    try:
        all_all_info = get_collection_python("AllInfo")
        all_info_keys = []
        target = None
        for a in all_all_info:
            if a["id"] == doc:
                print(a)
                curr_keys = list(a.keys())
                curr_keys.pop()
                all_info_keys = curr_keys
                target = a
        if target is not None:
            for t in target:
                if t in list(vals.keys()):  # vals.keys() will only ever have one key
                    print(list(vals.keys()))
                    all_all_info[all_all_info.index(target)][list(vals.keys())[0]] = (
                        vals[list(vals.keys())[0]]
                    )
                    final = all_all_info[all_all_info.index(target)]
                    for k in all_info_keys:
                        db.collection("AllInfo").document(doc).update({k: final[k]})
            return {"status": 0}
        return {"status": -13, "error_message": "No target found"}
    except Exception as e:
        return {"status": -1, "error_message": e}


def add_document_to_all_info_collection(doc):
    try:
        print(doc)
        first_part = db.collection("AllInfo").document(doc["id"])
        del doc["id"]
        first_part.set(doc)
        return {"status": 0}
    except Exception as e:
        print(e)
        return {"status": -1, "error_message": e}
