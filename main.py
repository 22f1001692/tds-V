import time
import uuid
from collections import defaultdict
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

request_id_context = ContextVar("request_id")

app = FastAPI()

# --- Middleware 1: Request Context ---
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_context.set(req_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

# --- Middleware 3: Per-Client Rate Limiting ---
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int, window: int):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.clients = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            now = time.time()
            self.clients[client_id] = [
                timestamp for timestamp in self.clients[client_id] 
                if now - timestamp < self.window
            ]
            if len(self.clients[client_id]) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"}
                )
            self.clients[client_id].append(now)
        return await call_next(request)

# ==========================================
# MIDDLEWARE REGISTRATION (Order matters)
# ==========================================

# Inner layers
app.add_middleware(RateLimitMiddleware, limit=9, window=10)
app.add_middleware(RequestContextMiddleware)

# Outer layer: CORS (Must be added last!)
origins = [
    "https://app-8z9tbt.example.com",
    "https://exam.sanand.workers.dev" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"] # This ensures the grader can read the header
)

# ==========================================
# ENDPOINT
# ==========================================
@app.get("/ping")
async def ping():
    return {
        "email": "22f1001692@ds.study.iitm.ac.in", 
        "request_id": request_id_context.get()
    }
