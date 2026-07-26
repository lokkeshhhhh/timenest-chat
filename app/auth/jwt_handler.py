from jose import jwt, JWTError, ExpiredSignatureError
from app.core.config import get_settings

settings = get_settings()

class InvalidTokenError(Exception):
    pass


def decode_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algo]
        )
    except ExpiredSignatureError:
        raise InvalidTokenError("Token has been expired.")
    except JWTError:
        raise InvalidTokenError("Token is invalid.")