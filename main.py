import time
import uuid
from collections import defaultdict
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to hold the request ID for the current async context
request_id_context = ContextVar("request_id")

app = FastAPI()

# --- Middleware 1: Request Context ---
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Read from header or generate a fresh UUID4
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # 2. Set the context variable
        request_id_context.set(req_id)
        
        # 3. Process the request
        response = await call_next(request)
        
        # 4. Add the request ID to the outgoing response headers
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
            
            # Clean up old requests outside the 10-second window
            self.clients[client_id] = [
                timestamp for timestamp in self.clients[client_id] 
                if now - timestamp < self.window
            ]
            
            # Enforce the 9 requests limit
            if len(self.clients[client_id]) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"}
                )
            
            # Record the new request timestamp
            self.clients[client_id].append(now)

        return await call_next(request)

# ==========================================
# MIDDLEWARE REGISTRATION
# Note: FastAPI applies middleware in reverse order.
# The last one added is the outermost layer.
# ==========================================

# Outer layer: CORS (Handles OPTIONS preflight before anything else)
origins = [
    "https://app-8z9tbt.example.com",
    # IMPORTANT: Add the actual origin of your exam platform below
    "https://exam.sanand.workers.dev" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middle layer: Rate Limit (9 requests per 10 seconds)
app.add_middleware(RateLimitMiddleware, limit=9, window=10)

# Inner layer: Request Context Propagation
app.add_middleware(RequestContextMiddleware)


# ==========================================
# ENDPOINT
# ==========================================
@app.get("/ping")
async def ping():
    return {
        # IMPORTANT: Replace with your actual logged-in email
        "email": "22f1001692@ds.study.iitm.ac.in", 
        "request_id": request_id_context.get()
    }
