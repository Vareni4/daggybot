from datetime import datetime, timedelta
import jwt
import hmac
import hashlib
import json
from urllib.parse import unquote
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION, BOT_TOKEN, ADMIN_USERS, AUTHORIZED_USERS, logger

security = HTTPBearer()

def create_jwt_token(user_data: dict) -> str:
    payload = user_data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

def verify_telegram_data(init_data: str) -> bool:
    try:
        logger.debug(f"Verifying Telegram data: {init_data}")
        # Parse the init data
        data = {k: unquote(v) for k, v in [s.split('=', 1) for s in init_data.split('&')]}
        logger.debug(f"data: {data}")
        
        # Remove hash from data
        received_hash = data.pop("hash", "")
        logger.debug(f"received_hash: {received_hash}")
        
        # Sort data alphabetically
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

        logger.debug(f"data_check_string: {data_check_string}")

        secret_key = hmac.new("WebAppData".encode(), BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()        
        logger.debug(f"calculated_hash: {calculated_hash}")
        
        if calculated_hash == received_hash:
            logger.debug("Telegram data verification successful")
            return True
        logger.warning("Telegram data verification failed: hash mismatch")
        return False
    except Exception as e:
        logger.error(f"Error verifying Telegram data: {str(e)}", exc_info=True)
        return False

def parse_user_data(init_data: str) -> dict:
    try:
        data = {k: unquote(v) for k, v in [s.split('=', 1) for s in init_data.split('&')]}
        if "user" not in data:
            logger.error(f"No \"user\" key info in init_data", exc_info=True)
            return None

        return json.loads(data["user"])
    except Exception as e:
        logger.error(f"Error pasring user_data from init_data: {str(e)}", exc_info=True)
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    logger.debug("Verifying JWT token")
    token = credentials.credentials
    user_data = verify_jwt_token(token)
    if user_data is None:
        logger.warning("Invalid or expired JWT token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    logger.debug(f"JWT token verified for user_id: {user_data.get('id')}")
    return user_data

def is_user_authorized(user_id: int) -> bool:
    logger.debug(f"Checking authorization for user {user_id}")
    is_authorized = user_id in AUTHORIZED_USERS
    logger.debug(f"User {user_id} authorization status: {is_authorized}")
    return is_authorized 

def is_user_admin(user_id: int) -> bool:
    logger.debug(f"Checking for user {user_id} is admin")
    is_admin = user_id in ADMIN_USERS
    logger.debug(f"User {user_id} admin status: {is_admin}")
    return is_admin 