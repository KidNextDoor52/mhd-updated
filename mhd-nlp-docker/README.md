# 🏋️‍♂️ MHD Athlete Data Hub

MHD is a platform for athletes and trainers to manage **medical records, training data, and equipment preferences** in one place.  

## 🚀 Features
- **User Sign-Up & Login** with JWT authentication.
- **Dashboard** for uploaded documents & forms.
- **Equipment Room** for tracking preferred gear (helmet, cleats, pads, etc.).
- **Weightroom** for performance metrics (bench, squat, 40yd, vertical).
- **Training Room** for injury/rehab/procedure records.
- **Docs Library** with uploads, filters, and secure share links.
- Future: **Mobile app (React Native)** + **SQL sidecar**.

---

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Auth:** OAuth2 + JWT
- **Frontend (current):** Jinja2 templates
- **Deployment:** Docker & Docker Compose

---

## 🏃 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)

### Run Locally
```bash
git clone <your-repo>
cd mhd-nlp-docker
docker-compose up --build
