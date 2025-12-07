# Simple Ticketing System

A lightweight, production-ready ticketing system built with FastAPI, SQLite, Bootstrap, and Vanilla JavaScript.

## 🚀 Features

### Public Request Form (`/`)
- Clean, user-friendly ticket submission interface
- Fields: Name, Email, Subject, Description, Priority
- Real-time validation and error handling
- Success confirmation with ticket number
- Responsive design with gradient UI

### Admin Dashboard (`/admin`)
- Complete ticket management interface
- Real-time statistics (Total, Open, In Progress, Resolved/Closed)
- Advanced filtering by Status and Priority
- Client-side search by name, email, or subject
- Inline ticket editing with modal dialog
- Auto-refresh every 30 seconds
- Responsive table layout

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🛠️ Installation & Setup

### 1. Project Structure

Create the following directory structure:

```
ticketing-system/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python dependencies
├── tickets.db             # SQLite database (auto-created)
└── static/
    ├── index.html         # Public request form
    └── admin.html         # Admin dashboard
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Create Static Folder

```bash
mkdir static
```

### 4. Place HTML Files

- Save `index.html` in the `static/` folder
- Save `admin.html` in the `static/` folder

## ▶️ Running the Application

### Start the Server

```bash
python main.py
```

Or with Uvicorn directly:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Access the Application

- **Public Request Form**: http://127.0.0.1:8000/
- **Admin Dashboard**: http://127.0.0.1:8000/admin
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/api/health

## 📡 API Endpoints

### Create Ticket
```http
POST /api/tickets
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Login issue",
  "description": "Cannot log in to my account...",
  "priority": "High"
}
```

### Get All Tickets
```http
GET /api/tickets?status=Open&priority=High
```

### Get Single Ticket
```http
GET /api/tickets/{ticket_id}
```

### Update Ticket
```http
PUT /api/tickets/{ticket_id}
Content-Type: application/json

{
  "status": "In Progress",
  "notes": "Investigating the issue..."
}
```

### Delete Ticket
```http
DELETE /api/tickets/{ticket_id}
```

## 🗄️ Database Schema

### Tickets Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| name | TEXT | Customer name |
| email | TEXT | Customer email |
| subject | TEXT | Ticket subject |
| description | TEXT | Detailed description |
| priority | TEXT | Low / Medium / High |
| status | TEXT | Open / In Progress / Resolved / Closed |
| notes | TEXT | Internal admin notes |
| created_at | TIMESTAMP | Auto-generated creation time |
| updated_at | TIMESTAMP | Auto-updated modification time |

## 🔒 Security Features

- **SQL Injection Prevention**: Parameterized queries via sqlite3
- **Input Validation**: Pydantic models with field constraints
- **XSS Prevention**: Client-side HTML escaping
- **CORS Protection**: Configurable CORS middleware
- **Type Safety**: Strong typing with Pydantic

## 🎨 UI/UX Highlights

### Request Form
- Modern gradient design with purple theme
- Priority selection with visual badges
- Character count validation
- Success/error alerts
- Mobile-responsive

### Admin Dashboard
- Real-time statistics cards
- Advanced filtering and search
- Modal-based ticket editing
- Status color coding
- Auto-refresh functionality
- Hover effects and smooth transitions

## 📊 Status & Priority Values

### Status Options
- **Open**: New ticket, not yet addressed
- **In Progress**: Currently being worked on
- **Resolved**: Issue fixed, awaiting confirmation
- **Closed**: Ticket completed and closed

### Priority Levels
- **Low**: Minor issues, low urgency
- **Medium**: Standard priority (default)
- **High**: Critical issues requiring immediate attention

## 🔧 Customization

### Change Port
Edit `main.py` or run:
```bash
uvicorn main:app --port 8080
```

### Database Location
Change `DB_NAME` in `main.py`:
```python
DB_NAME = "path/to/your/tickets.db"
```

### CORS Configuration
Modify CORS settings in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://yourdomain.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## 🧪 Testing the API

### Using cURL
```bash
# Create a ticket
curl -X POST http://127.0.0.1:8000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","subject":"Test","description":"Test description test","priority":"High"}'

# Get all tickets
curl http://127.0.0.1:8000/api/tickets

# Update ticket status
curl -X PUT http://127.0.0.1:8000/api/tickets/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"Resolved"}'
```

### Using Python Requests
```python
import requests

# Create ticket
response = requests.post('http://127.0.0.1:8000/api/tickets', json={
    'name': 'Jane Smith',
    'email': 'jane@example.com',
    'subject': 'Feature request',
    'description': 'Would like to see dark mode added',
    'priority': 'Medium'
})
print(response.json())
```

## 🚦 Troubleshooting

### Database Locked Error
- Close any SQLite browser/viewer accessing the database
- Ensure only one server instance is running

### Port Already in Use
```bash
# Change port
uvicorn main:app --port 8001
```

### Module Not Found
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### CORS Errors
- Check that frontend and backend URLs match
- Verify CORS middleware configuration

## 📈 Future Enhancements

- [ ] User authentication and role-based access
- [ ] Email notifications for ticket updates
- [ ] File attachment support
- [ ] Ticket assignment to team members
- [ ] SLA tracking and escalation
- [ ] Advanced reporting and analytics
- [ ] Export tickets to CSV/PDF
- [ ] Webhook integrations
- [ ] Multi-language support

## 📝 License

This project is provided as-is for educational and commercial use.

## 👨‍💻 Support

For issues or questions:
1. Check the FastAPI documentation: https://fastapi.tiangolo.com/
2. Review the code comments for inline documentation
3. Test API endpoints using the built-in Swagger UI at `/docs`

---

**Built with ❤️ using FastAPI, SQLite, Bootstrap, and Vanilla JavaScript**





==============


🚀 How to Use
1. Directory Structure
ticketing-system/
├── main.py              # FastAPI backend
├── requirements.txt     # Dependencies
├── tickets.db          # SQLite (auto-created)
└── static/
    ├── index.html      # ← Place this file here
    └── admin.html      # ← Place this file here
2. Quick Start
bash# Install dependencies
pip install -r requirements.txt

# Create static folder
mkdir static

# Save index.html to static/index.html
# Save admin.html to static/admin.html

# Run server
python main.py
3. Access URLs

Request Form: http://127.0.0.1:8000/
Admin Dashboard: http://127.0.0.1:8000/admin
API Docs: http://127.0.0.1:8000/docs


🎯 New Features Added
Request Form Enhancements:
✅ Real-time character counter
✅ Form field validation on blur
✅ Priority badge animations
✅ Auto-hide alerts (5-10 seconds)
✅ Better error handling with detailed messages
✅ Security footer badge
Admin Dashboard Enhancements:
✅ Toast notifications (top-right corner)
✅ Relative timestamps ("5m ago")
✅ Debounced search (300ms delay)
✅ Auto-refresh with timestamp
✅ Loading overlay with blur
✅ Empty state illustrations
✅ Truncated text with tooltips
✅ Email mailto: links
✅ Status emojis (🟡🔵🟢⚫)
✅ Cleanup on page unload

📱 Responsive Design
Both pages are fully responsive:

Mobile (< 768px): Stacked layout, compact tables
Tablet (768px - 1024px): Two-column filters
Desktop (> 1024px): Full layout with all features


🔒 Security Features
✅ HTML escaping on all user inputs
✅ XSS prevention
✅ CORS protection
✅ Input validation (client + server)
✅ Parameterized SQL queries

🎨 Color Scheme

Primary: Purple gradient (#667eea → #764ba2)
Success: Green (#28a745)
Warning: Yellow (#ffc107)
Danger: Red (#dc3545)
Info: Blue (#0dcaf0)


You now have two production-ready, enterprise-grade HTML files with modern UI/UX, complete validation, error handling, and responsive design! 🎉