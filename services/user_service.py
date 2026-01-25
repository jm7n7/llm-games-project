import json
import secrets
import string
import logging
import bcrypt
from google.cloud import storage

logger = logging.getLogger(__name__)

BUCKET_NAME = "user-logins"

def _get_bucket():
    """Returns the GCS bucket object."""
    try:
        storage_client = storage.Client()
        return storage_client.bucket(BUCKET_NAME)
    except Exception as e:
        logger.error(f"Failed to connect to GCS: {e}")
        return None

def generate_password(length=10):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def _hash_password(plain_password):
    """Hashes a password using bcrypt."""
    # bcrypt requires bytes
    password_bytes = plain_password.encode('utf-8')
    # Generate salt and hash
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8') # Store as string

def _check_password(plain_password, hashed_password):
    """Verifies a password against a hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_user(username, email, first_name):
    """
    Creates a new user in GCS.
    Returns the generated plain-text password if successful, or None.
    """
    bucket = _get_bucket()
    if not bucket: return None

    blob_name = f"{username}.json"
    blob = bucket.blob(blob_name)

    if blob.exists():
        logger.warning(f"User {username} already exists.")
        return None # User already exists

    # Generate and hash password
    plain_password = generate_password()
    password_hash = _hash_password(plain_password)

    user_data = {
        "username": username,
        "email": email,
        "first_name": first_name,
        "password_hash": password_hash
    }

    try:
        blob.upload_from_string(json.dumps(user_data), content_type='application/json')
        logger.info(f"User {username} created successfully.")
        return plain_password
    except Exception as e:
        logger.error(f"Failed to create user {username}: {e}")
        return None

def authenticate_user(username, password):
    """
    Verifies user credentials.
    Returns user data (dict) if valid, None otherwise.
    """
    bucket = _get_bucket()
    if not bucket: return None

    blob_name = f"{username}.json"
    blob = bucket.blob(blob_name)

    if not blob.exists():
        return None

    try:
        data_str = blob.download_as_text()
        user_data = json.loads(data_str)
        
        stored_hash = user_data.get("password_hash")
        if stored_hash and _check_password(password, stored_hash):
            return user_data
        
    except Exception as e:
        logger.error(f"Authentication error for {username}: {e}")
    
    return None

def reset_password(username):
    """
    Resets the user's password to a new random one.
    Returns: (email, new_plain_password) if successful, (None, None) otherwise.
    """
    bucket = _get_bucket()
    if not bucket: return None, None

    blob_name = f"{username}.json"
    blob = bucket.blob(blob_name)

    if not blob.exists():
        return None, None

    try:
        data_str = blob.download_as_text()
        user_data = json.loads(data_str)

        # Generate new password
        new_password = generate_password()
        new_hash = _hash_password(new_password)

        # Update data
        user_data["password_hash"] = new_hash
        
        # Save back to GCS
        blob.upload_from_string(json.dumps(user_data), content_type='application/json')
        
        return user_data.get("email"), new_password

    except Exception as e:
        logger.error(f"Password reset failed for {username}: {e}")
        return None, None
