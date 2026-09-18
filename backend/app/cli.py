"""Management CLI.

Usage:
    python -m app.cli create-admin

Creates a production PI account without demo credentials.
Password comes from ADMIN_PASSWORD env or an interactive prompt (hidden).
"""

import getpass
import logging
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User

logger = logging.getLogger("labflow.cli")


def create_admin() -> None:
    username = (os.environ.get("ADMIN_USERNAME") or input("管理员用户名: ")).strip()
    name = (os.environ.get("ADMIN_NAME") or input("显示姓名: ")).strip() or username
    email = (os.environ.get("ADMIN_EMAIL") or input("邮箱: ")).strip()
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass(
        "密码（至少 8 位）: "
    )

    if not username or not email:
        sys.exit("错误：用户名与邮箱不能为空")
    if len(password) < 8:
        sys.exit("错误：密码长度至少 8 位")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)):
            sys.exit(f"错误：用户名 {username} 已存在")
        if db.scalar(select(User).where(User.email == email)):
            sys.exit(f"错误：邮箱 {email} 已被使用")
        user = User(
            username=username,
            name=name,
            email=email,
            role="PI",
            password_hash=hash_password(password),
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        logger.info("管理员已创建: %s (id=%s)", username, user.id)


COMMANDS = {
    "create-admin": create_admin,
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    command = sys.argv[1] if len(sys.argv) > 1 else None
    if command not in COMMANDS:
        sys.exit(f"用法: python -m app.cli {'|'.join(COMMANDS)}")
    COMMANDS[command]()


if __name__ == "__main__":
    main()
