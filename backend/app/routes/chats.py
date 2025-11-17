from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from bson import ObjectId

from ..database import get_db
from ..models import ChatPublic, MessageCreate, MessagePublic
from ..services.nlp import generate_bot_response
from ..security import JWT_SECRET


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
	try:
		payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])  # type: ignore[arg-type]
		user_id: str = payload.get("sub")
		if not user_id:
			raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
		return user_id
	except JWTError:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def serialize_chat(doc: Dict[str, Any]) -> ChatPublic:
	return ChatPublic(id=str(doc["_id"]), createdAt=doc["createdAt"])


def serialize_message(doc: Dict[str, Any]) -> MessagePublic:
	return MessagePublic(
		id=str(doc["_id"]),
		sender=doc["sender"],
		text=doc["text"],
		timestamp=doc["timestamp"],
	)


@router.post("/", response_model=ChatPublic)
async def create_chat(user_id: str = Depends(get_current_user_id), db=Depends(get_db)) -> ChatPublic:
	chat_doc = {
		"userId": ObjectId(user_id),
		"createdAt": datetime.now(tz=timezone.utc),
	}
	res = await db.chats.insert_one(chat_doc)
	chat_doc["_id"] = res.inserted_id
	return serialize_chat(chat_doc)


@router.get("/", response_model=List[ChatPublic])
async def list_chats(user_id: str = Depends(get_current_user_id), db=Depends(get_db)) -> List[ChatPublic]:
	chats = []
	async for doc in db.chats.find({"userId": ObjectId(user_id)}).sort("createdAt", -1):
		chats.append(serialize_chat(doc))
	return chats


@router.post("/{chat_id}/message", response_model=MessagePublic)
async def send_message(chat_id: str, payload: MessageCreate, user_id: str = Depends(get_current_user_id), db=Depends(get_db)) -> MessagePublic:
	chat = await db.chats.find_one({"_id": ObjectId(chat_id), "userId": ObjectId(user_id)})
	if not chat:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

	user_msg = {
		"chatId": ObjectId(chat_id),
		"sender": "user",
		"text": payload.text,
		"timestamp": datetime.now(tz=timezone.utc),
	}
	res = await db.messages.insert_one(user_msg)
	user_msg["_id"] = res.inserted_id

	bot_text = await generate_bot_response(payload.text, db, chat_id)
	bot_msg = {
		"chatId": ObjectId(chat_id),
		"sender": "bot",
		"text": bot_text,
		"timestamp": datetime.now(tz=timezone.utc),
	}
	res2 = await db.messages.insert_one(bot_msg)
	bot_msg["_id"] = res2.inserted_id
	return serialize_message(bot_msg)


@router.get("/{chat_id}/messages", response_model=List[MessagePublic])
async def get_messages(chat_id: str, user_id: str = Depends(get_current_user_id), db=Depends(get_db)) -> List[MessagePublic]:
	chat = await db.chats.find_one({"_id": ObjectId(chat_id), "userId": ObjectId(user_id)})
	if not chat:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
	messages: List[MessagePublic] = []
	async for doc in db.messages.find({"chatId": ObjectId(chat_id)}).sort("timestamp", 1):
		messages.append(serialize_message(doc))
	return messages


