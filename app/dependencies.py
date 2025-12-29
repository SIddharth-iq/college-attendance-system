from fastapi import Depends, HTTPException, status
from sqlalchemy.sql.functions import current_user
from app.models import User, RoleEnum
from app.routers.auth import get_current_user


def require_role(allowed_roles: list[RoleEnum]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized"
            )
        return current_user

    return role_checker
