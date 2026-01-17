"""
Role-based authorization dependencies for multi-tenant account access control.

Provides dependencies for:
- Role hierarchy enforcement (owner > admin > member > viewer)
- Account-scoped access validation
- Super admin bypass logic
"""

from fastapi import Depends, HTTPException

from app.models.auth_models import TokenPayload
from app.dependencies.jwt_auth_dependency import get_current_user
from common.service_connections.db_service.database.enums import AccountRoleEnum


# Role hierarchy values for comparison
ROLE_HIERARCHY = {
    AccountRoleEnum.OWNER.value: 4,
    AccountRoleEnum.ADMIN.value: 3,
    AccountRoleEnum.MEMBER.value: 2,
    AccountRoleEnum.VIEWER.value: 1,
}


def validate_account_access(
    token: TokenPayload,
    requested_account_id: str,
    allow_super_admin: bool = True,
) -> None:
    """
    Validate that a user can access a specific account.

    Args:
        token: Decoded JWT token payload
        requested_account_id: Account ID being accessed
        allow_super_admin: Whether super admins bypass account check (default True)

    Raises:
        HTTPException: 403 if user cannot access the account
    """
    # Super admins can access any account (unless explicitly disabled)
    if allow_super_admin and token.is_super_admin:
        return

    # Check if token has account context
    if not token.account_id:
        raise HTTPException(
            status_code=403,
            detail="No account context in token. Please switch to an account first.",
        )

    # Validate account match
    if token.account_id != requested_account_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You do not have access to this account.",
        )


def require_account_role(
    min_role: str,
    allow_super_admin: bool = True,
):
    """
    Create a dependency that requires a minimum account role.

    Args:
        min_role: Minimum required role (owner/admin/member/viewer)
        allow_super_admin: Whether super admins bypass role check (default True)

    Returns:
        FastAPI dependency function

    Example:
        @router.post("/sensitive-action")
        async def action(token: TokenPayload = Depends(require_account_role("admin"))):
            # Only admins and owners can access
    """

    def role_checker(token: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        """
        Check if user has minimum required role in their active account.

        Args:
            token: Decoded JWT token payload

        Returns:
            TokenPayload if authorized

        Raises:
            HTTPException: 403 if insufficient role or no account context
        """
        # Super admins bypass role checks (unless explicitly disabled)
        if allow_super_admin and token.is_super_admin:
            return token

        # Check if token has account context
        if not token.account_role:
            raise HTTPException(
                status_code=403,
                detail="No account role in token. Please switch to an account first.",
            )

        # Get role hierarchy values
        min_role_value = ROLE_HIERARCHY.get(min_role)
        user_role_value = ROLE_HIERARCHY.get(token.account_role)

        if not min_role_value:
            raise ValueError(f"Invalid min_role: {min_role}")

        if not user_role_value:
            raise HTTPException(
                status_code=403,
                detail=f"Invalid role in token: {token.account_role}",
            )

        # Check role hierarchy
        if user_role_value < min_role_value:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {min_role} role or higher required.",
            )

        return token

    return role_checker


# Convenience dependencies for common role checks
def require_owner(
    token: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Require user to be an account owner.

    Args:
        token: Decoded JWT token payload

    Returns:
        TokenPayload if user is owner or super admin

    Raises:
        HTTPException: 403 if user is not owner
    """
    return require_account_role(AccountRoleEnum.OWNER.value)(token)


def require_admin(
    token: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Require user to be an account admin or higher.

    Args:
        token: Decoded JWT token payload

    Returns:
        TokenPayload if user is admin, owner, or super admin

    Raises:
        HTTPException: 403 if user role is below admin
    """
    return require_account_role(AccountRoleEnum.ADMIN.value)(token)


def require_member(
    token: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Require user to be an account member or higher.

    Args:
        token: Decoded JWT token payload

    Returns:
        TokenPayload if user is member, admin, owner, or super admin

    Raises:
        HTTPException: 403 if user role is viewer
    """
    return require_account_role(AccountRoleEnum.MEMBER.value)(token)


def require_viewer(
    token: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Require user to have at least viewer role (all authenticated users with account access).

    Args:
        token: Decoded JWT token payload

    Returns:
        TokenPayload if user has any account role

    Raises:
        HTTPException: 403 if user has no account context
    """
    return require_account_role(AccountRoleEnum.VIEWER.value)(token)


def require_super_admin(
    token: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Require user to be a super admin.

    Super admins can access all accounts and have full system privileges.

    Args:
        token: Decoded JWT token payload

    Returns:
        TokenPayload if user is super admin

    Raises:
        HTTPException: 403 if user is not super admin
    """
    if not token.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Super admin access required.",
        )
    return token
