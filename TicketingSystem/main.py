from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import sqlite3
import os

# Timezone configuration for Philippines (UTC+8)
PHILIPPINES_TZ = timezone(timedelta(hours=8))

# Initialize FastAPI app
app = FastAPI(title="Simple Ticketing System", version="1.0.0")

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_NAME = "tickets.db"

# Pydantic models for request/response validation
class TicketCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    priority: Optional[str] = Field(default="Medium", pattern="^(Low|Medium|High)$")

class TicketUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(Open|In Progress|Resolved|Closed)$")
    notes: Optional[str] = Field(None, max_length=2000)

class TicketResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: str
    description: str
    priority: str
    status: str
    notes: Optional[str]
    created_at: str
    updated_at: str

# Database initialization
def init_db():
    """Initialize SQLite database with tickets table"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_philippines_time():
    """Get current time in Philippines timezone (UTC+8)"""
    return datetime.now(PHILIPPINES_TZ).strftime('%Y-%m-%d %H:%M:%S')

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print(f"✓ Database initialized: {DB_NAME}")
    print("✓ Server running on http://127.0.0.1:8000")

@app.get("/")
async def root():
    """Serve the request form page"""
    return FileResponse("static/index.html")

@app.get("/admin")
async def admin():
    """Serve the admin servicing page"""
    return FileResponse("static/admin.html")

@app.post("/api/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket: TicketCreate):
    """Create a new support ticket"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = get_philippines_time()
        
        cursor.execute("""
            INSERT INTO tickets (name, email, subject, description, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)
        """, (ticket.name, ticket.email, ticket.subject, ticket.description, ticket.priority, current_time, current_time))
        
        ticket_id = cursor.lastrowid
        conn.commit()
        
        # Fetch the created ticket
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row)
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/tickets", response_model=List[TicketResponse])
async def get_tickets(status: Optional[str] = None, priority: Optional[str] = None):
    """Get all tickets with optional filtering"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM tickets WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int):
    """Get a single ticket by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return dict(row)
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: int, ticket_update: TicketUpdate):
    """Update ticket status and/or notes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if ticket exists
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        if ticket_update.status is not None:
            update_fields.append("status = ?")
            params.append(ticket_update.status)
        
        if ticket_update.notes is not None:
            update_fields.append("notes = ?")
            params.append(ticket_update.notes)
        
        if not update_fields:
            conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Always update the updated_at timestamp with Philippines time
        update_fields.append("updated_at = ?")
        params.append(get_philippines_time())
        params.append(ticket_id)
        
        query = f"UPDATE tickets SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        # Fetch updated ticket
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row)
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/api/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: int):
    """Delete a ticket (optional, for admin cleanup)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        conn.commit()
        conn.close()
        
        return None
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy", 
        "timestamp": get_philippines_time(),
        "timezone": "Asia/Manila (UTC+8)"
    }

# Mount static files (HTML/CSS/JS)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")