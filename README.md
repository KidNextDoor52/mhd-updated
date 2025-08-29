# 🧠 MHD NLP Portal

A secure, containerized medical portal built with **FastAPI**, **MongoDB**, and **scispaCy**. This system enables authenticated users to:
- Upload and NLP-analyze medical documents
- Submit structured medical history forms
- View and filter dashboard data
- Share documents/forms securely via password-protected, expiring links

---

## 📦 Features

- 🔐 Token-based login system with FastAPI OAuth2
- 📄 Medical document upload and NLP entity extraction
- 📝 Athlete medical history form submission
- 📊 Dashboard with filtering by tags and upload dates
- 🔗 Secure, expiring resource share links
- 🧬 NLP powered by **scispaCy** with fallback to **spaCy**

---

## 🛠️ Stack

- **Backend**: FastAPI (Python 3.10), Pydantic, Jinja2
- **NLP**: spaCy / scispaCy
- **Database**: MongoDB (via Docker)
- **Auth**: OAuth2 + JWT (python-jose)
- **Containerized**: Docker + Docker Compose

---

## 🚀 Quick Start (with Docker)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/mhd-nlp-portal.git
cd mhd-nlp-portal
2. Create environment file
Create a file at app/.env.dev:

dotenv
Copy
MONGO_URI=mongodb://mongo:27017
MONGO_DB=mhd_dev
SECRET_KEY=your-super-secret-key
3. Build and run the project
bash
Copy
docker-compose up --build
App runs on: http://localhost:8000

MongoDB runs on: localhost:27017

🧪 API Overview
🔐 Auth
Endpoint	Method	Description
/signup	POST	Register a new user
/token	POST	Get access token (OAuth2)

📄 Documents
Endpoint	Method	Description
/upload	POST	Upload and NLP-process file
/dashboard	GET	View uploaded docs + filter

🧾 Forms
Endpoint	Method	Description
/form/create	GET/POST	Submit medical history

🔗 Share
Endpoint	Method	Description
/share	POST	Generate shareable resource link
/shared/{id}	GET	Access a shared doc or form

📂 Folder Structure
bash
Copy
.
│
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── equipment.py
│   │   ├── weightroom.py
│   │   ├── upload.py
│   │   └── training.py
│   └── ...
│
├── templates/
│   ├── index.html
│   ├── dashboard.html
│   ├── equipment_room.html
│   ├── weightroom.html
│   ├── upload_record.html
│   ├── training_room.html
│   └── ...
│
├── static/
│   ├── css/style.css
│   ├── js/equipment.js
│   ├── js/weightroom.js
│   ├── js/upload.js
│   ├── js/training.js
│   └── videos/
│       ├── equipment_intro.mp4
│       ├── weightroom_intro.mp4
│       ├── upload_intro.mp4
│       └── training_intro.mp4
│
└── requirements.txt
└── README.md
📖 Development Tips
You can test authenticated endpoints using Postman or cURL by retrieving a token from /token and adding it to the Authorization header as Bearer <token>.

If you update Python files, you may need to rebuild your container:

bash
Copy
docker-compose down -v
docker-compose up --build
✅ TODO Checklist
 Login + Signup Flow

 File Upload + NLP

 Dashboard with Filters

 Medical Form Submission

 Secure Share Links

 Add HTML for Shared Form/Doc Viewing

 Logout / Session Expiry Handling

🧠 NLP Models
Uses en_core_sci_sm for medical entity detection

Falls back to en_core_web_sm if unavailable

You can customize file_processor.py to enhance entity matching

📃 License
MIT License © 2025

yaml
Copy

---

Let me know if you want to add:
- Screenshots
- API examples with cURL/Postman
- Contributor section

Or I can generate this as a downloadable file.
