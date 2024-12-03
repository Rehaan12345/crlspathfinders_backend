import inspect
import time
from firebase_admin import storage


# Global variable to cache the bucket object
_cached_bucket = None
def log_error(error_message):
    """
    Appends an error message to a log file and uploads it to Firebase Storage.
    File name format is "Jan-01-1970.txt".
    The log includes:
        HH:MM:SS | filepath | line number
        Error message
  
    @param error_message (str): The error message to log.
    @return: None
    """
    # uses inspect package to get file name and line numbe where log_error was run
    caller_frame = inspect.currentframe().f_back
    frame_info = inspect.getframeinfo(caller_frame)
    filename = frame_info.filename
    line_num = frame_info.lineno
    # generate log content
    log_content = f"{time.strftime('%H:%M:%S')} | {filename} | line #{line_num}\n{error_message}\n\n"
    # file name for today's log file
    file_name = f"{time.strftime('%b-%d-%Y')}.txt"
    local_log_path = f"/tmp/{file_name}"  # tempoary local storage path for the file
    # write the log content to the file
    try:
        global _cached_bucket
        if _cached_bucket is None:
            _cached_bucket = storage.bucket()  # check for cached bucket, if not found, then pull the default bucket from db
        bucket = _cached_bucket
        
        with open(local_log_path, "a+") as logfile:
            logfile.write(log_content)
    except Exception as e:
        print(f"Failed to write log to file: {str(e)}")
    # upload the log file to firebase storage
    try:
        blob = bucket.blob(f"errorlogs/{file_name}")
        blob.upload_from_filename(local_log_path)
    except Exception as e:
        print(f"Failed to upload log to Firebase: {str(e)}")