from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, user_data: UserCreate) -> User:
        # Pre-checks give specific error messages; IntegrityError is the safety net for races.
        if self.db.execute(select(User).where(User.email == user_data.email)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        if self.db.execute(select(User).where(User.username == user_data.username)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password),
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username already taken",
            )
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user and user.is_active and verify_password(password, user.hashed_password):
            return user
        return None

    def create_token(self, user: User) -> Token:
        access_token = create_access_token({"sub": str(user.id)})
        return Token(access_token=access_token, token_type="bearer")
