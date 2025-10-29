from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.auth import router as auth_router  # adjust import if necessary
from backend.routes.chat import router as chat_router

app = FastAPI()

# Enable CORS for your frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your auth router
app.include_router(auth_router)
app.include_router(chat_router)
