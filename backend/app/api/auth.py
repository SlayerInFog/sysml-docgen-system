from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, require_roles, verify_password
from app.models.user import User
from app.schemas.auth import TokenOut, UserCreate, UserLogin, UserOut, UserUpdate
from app.services.audit import write_log

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if payload.role not in {"author", "reader"}:
        raise HTTPException(status_code=400, detail="自助注册只能选择 author 或 reader")
    exists = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_log(db, user, "register", "user", user.id, "用户注册")
    return user


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已停用")
    token = create_access_token(user.username, {"role": user.role})
    write_log(db, user, "login", "user", user.id, "用户登录")
    return TokenOut(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
def users(
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/users/options", response_model=list[UserOut])
def user_options(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[User]:
    return db.query(User).filter(User.is_active.is_(True)).order_by(User.username.asc()).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None:
        if user.id == admin.id:
            raise HTTPException(status_code=400, detail="Cannot change the current admin role")
        if payload.role not in {"author", "reader"}:
            raise HTTPException(status_code=400, detail="Role updates only support author or reader")
        user.role = payload.role
    if payload.is_active is not None:
        if user.id == admin.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot disable the current admin account")
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    write_log(db, admin, "update_user", "user", user.id, f"{user.username}:{user.role}:{user.is_active}")
    return user
