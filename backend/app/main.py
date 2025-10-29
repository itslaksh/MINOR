from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.auth import router as auth_router
from .routes.chats import router as chats_router
from .services.nlp import load_nlp_resources, seed_default_faqs
from .database import connect_to_mongo, close_mongo_connection


app = FastAPI(title="DoJ Chatbot API", version="1.0.0")


app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
	await connect_to_mongo()
	await load_nlp_resources()
	# Knowledge base is loaded from backend/knowledge_base.txt by load_nlp_resources().


@app.on_event("shutdown")
async def on_shutdown() -> None:
	await close_mongo_connection()


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(chats_router, prefix="/chats", tags=["chats"])
from .routes.admin import router as admin_router
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(voice_router,prefix="/voice",tags=['voice'])


@app.get("/health")
async def health() -> dict:
	return {"status": "ok"}


