from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.jwt_handler import decode_jwt, InvalidTokenError
from app.core.database import get_db
from app.models.user import User


class AuthContext:
    """
    Ek verified request ka context — jaisa Laravel me auth()->user() +
    tenant_organization() dono ka combined result.
    """
    def __init__(self, user_id: int, user_uuid: str, organization_uuid: str, role: str | None):
        self.user_id = user_id
        self.user_uuid = user_uuid
        self.organization_uuid = organization_uuid
        self.role = role


async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Poora JWT verification flow:
    1. Decode + signature/expiry verify
    2. guard check (temp tokens reject)
    3. organization_uuid null check
    4. token_version DB match (revocation check)
    """
    try:
        payload = decode_jwt(token)
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    # Step 2: guard check — temp tokens (password reset, 2FA) ko chat access nahi milega
    guard = payload.get("guard")
    if guard == "temp":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Temporary tokens cannot access chat")

    # Step 3: organization_uuid honi hi chahiye
    organization_uuid = payload.get("organization_uuid")
    if not organization_uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No organization context in token")

    user_uuid = payload.get("user_uuid")
    if not user_uuid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Step 4: token_version DB se match karo (revocation check)
    result = await db.execute(select(User).where(User.uuid == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_version_in_jwt = payload.get("token_version")
    if token_version_in_jwt != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    return AuthContext(
        user_id=user.id,
        user_uuid=user.uuid,
        organization_uuid=organization_uuid,
        role=payload.get("role"),
    )