import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv, dotenv_values


def _load_env() -> None:
	backend_root = Path(__file__).resolve().parent.parent
	for candidate in [backend_root / ".env", Path.cwd() / ".env"]:
		if candidate.exists():
			values = dotenv_values(dotenv_path=str(candidate))
			for key, value in values.items():
				if value is not None:
					os.environ[key] = value
			break


_load_env()


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Inline fallback for development per user's request
JWT_SECRET = os.getenv("JWT_SECRET") or "your_jwt_secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12


def hash_password(password: str) -> str:
	return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
	return pwd_context.verify(plain_password, password_hash)


def create_access_token(sub: str, expires_delta: Optional[timedelta] = None) -> str:
	if not JWT_SECRET:
		raise RuntimeError("JWT_SECRET is not set")
	expire = datetime.now(tz=timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
	to_encode = {"sub": sub, "exp": expire}
	encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
	return encoded_jwt


