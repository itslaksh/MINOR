# DoJ Chatbot – Full-Stack Setup Guide

This repository hosts a citizen-facing chatbot for the Department of Justice prototype. It consists of a FastAPI backend that handles authentication, chat storage, and Gemini-powered responses, plus a React/Vite frontend that renders the chat UI.

## Project Layout

```
backend/   # FastAPI app, NLP services, MongoDB access, knowledge base
frontend/  # React 19 + Vite UI with routing and chat experience
```

## Prerequisites

- **Python** 3.11+ (tested with 3.13 via `venv/pyvenv.cfg`)
- **Node.js** 18+ (Node 20 LTS recommended) and npm
- **MongoDB** database (Atlas cluster or local instance)
- **Google AI Studio** API key for Gemini (`GEMINI_API_KEY`)
- Internet access on first backend startup (downloads `sentence-transformers/all-MiniLM-L6-v2`)

> Tip: If you need GPU acceleration or custom Torch builds, install them before `pip install -r requirements.txt`.

## Backend Setup

1. **Create and activate a virtual environment**
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\activate     # PowerShell
   # source .venv/bin/activate  # bash/zsh
   ```

2. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure environment variables** by creating `backend/.env`:
   ```
   MONGODB_URI=mongodb+srv://<user>:<pass>@cluster/<db>?retryWrites=true&w=majority
   JWT_SECRET=replace_with_long_random_string
   GEMINI_API_KEY=ai_studio_key_here
   ADMIN_TOKEN=optional_admin_header_value
   ```
   - `MONGODB_URI` is required in production. A fallback Atlas URI exists for dev only.
   - `JWT_SECRET` secures issued tokens; never ship the default value.
   - `GEMINI_API_KEY` enables Google Generative AI responses.
   - `ADMIN_TOKEN` gates the `/admin/*` maintenance routes (optional but recommended).

4. **Seed or edit the knowledge base**
   - Content lives in `backend/knowledge_base.txt`. Edit this file to update chatbot knowledge.
   - After editing while the server is running, call `POST /admin/reindex` with the `admin-token` header to rebuild embeddings without restarting.

5. **Run the API locally**
   ```bash
   uvicorn app.main:app --reload --port 8000
   # or
   python uvicorn_app.py
   ```

### Backend Endpoints Overview

- `POST /auth/register` – create a user (email + password)
- `POST /auth/login` – obtain a JWT bearer token
- `GET /chats` / `POST /chats` – list or create chats (auth required)
- `GET /chats/{chatId}/messages` – fetch conversation history
- `POST /chats/{chatId}/message` – send a message and receive the bot reply
- `POST /admin/reindex` – reload `knowledge_base.txt` (requires `ADMIN_TOKEN` if set)
- `GET /admin/debug_query?q=<text>` – inspect vector matches (also admin-guarded)
- `GET /health` – basic readiness probe

## Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure the API base URL** by creating `frontend/.env` (or `.env.local`):
   ```
   VITE_API_URL=http://localhost:8000
   ```

3. **Run the development server**
   ```bash
   npm run dev
   ```
   Vite defaults to `http://localhost:5173`. The app expects the backend to be reachable at `VITE_API_URL`.

### Frontend Highlights

- React 19 with Vite 7 and TypeScript
- Global auth context (`src/auth/AuthContext.tsx`) stores JWT tokens and injects them via Axios (`src/lib/api.ts`)
- Pages under `src/pages` include login, registration, chat, profile, and settings screens
- UI components (e.g., `Navbar`, `MessageBubble`) rely on Tailwind CSS 4 (via `@tailwindcss/vite`)

## Running the Full Stack

1. Start the FastAPI server (`uvicorn app.main:app --reload --port 8000`).
2. Start the Vite dev server (`npm run dev` in `frontend/`).
3. Visit `http://localhost:5173`.
4. Register a new user, sign in, create a chat, and begin messaging. The frontend automatically persists the JWT and attaches it to API calls.

## Useful Commands

| Task | Command |
| --- | --- |
| Backend lint/type-check (via FastAPI) | `uvicorn app.main:app --reload` |
| Backend prod server (example) | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Frontend dev | `npm run dev` |
| Frontend production build | `npm run build` then `npm run preview` |
| Run ESLint (frontend) | `npm run lint` |

## Troubleshooting

- **Torch install fails on Windows**: install the appropriate wheel from https://pytorch.org/get-started/locally/ before running `pip install -r requirements.txt`, then rerun the requirements install.
- **Gemini errors**: ensure `GEMINI_API_KEY` is valid and the machine can reach Google APIs. Logs during startup will print whether Gemini initialized successfully.
- **Knowledge base edits not reflected**: call `POST /admin/reindex` (with `admin-token` header if `ADMIN_TOKEN` is set) after saving `knowledge_base.txt`.
- **CORS issues**: `app/main.py` currently allows all origins for development; adjust the whitelist before deploying to production.

## Next Steps

- Harden secrets management (use environment-specific values instead of inline fallbacks).
- Add automated tests for API routes and React components.
- Containerize backend and frontend or add docker-compose for one-command spins.

Happy hacking!


