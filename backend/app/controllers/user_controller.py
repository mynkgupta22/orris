from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse, PasswordChangeRequest
from app.core.security import SecurityService


class UserController:
    
    async def get_profile(self, current_user: User) -> UserResponse:
        """Get current user profile"""
        return UserResponse.from_orm(current_user)

    async def update_profile(
        self,
        user_update: UserUpdate,
        current_user: User,
        db: AsyncSession
    ) -> UserResponse:
        """Update current user profile"""
        
        update_data = user_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse.from_orm(current_user)

    async def change_password(
        self,
        password_request: PasswordChangeRequest,
        current_user: User,
        db: AsyncSession
    ) -> dict:
        """Change user password"""
        
        # Check if user has a password (not OAuth user)
        if not current_user.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change password for OAuth users"
            )
        
        # Verify current password
        if not SecurityService.verify_password(password_request.current_password, current_user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password strength
        is_strong, message = SecurityService.validate_password_strength(password_request.new_password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Update password
        current_user.password = SecurityService.get_password_hash(password_request.new_password)
        
        await db.commit()
        
        return {"message": "Password updated successfully"}

    async def get_user_by_id(self, user_id: int, db: AsyncSession) -> UserResponse:
        """Get user by ID (admin only)"""
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.from_orm(user)