# 📍 Postal Code Genesis Platform

> **Building Addresses Where None Exist** — A complete platform for creating postal code systems in developing nations.

## Architecture

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL + PostGIS |
| API | FastAPI (Python 3.11) |
| Frontend | React 18 |
| Maps | Google Maps SDK / Leaflet fallback |
| Mobile | React Native (field workers) |
| Deployment | Docker Compose |

## Quick Start

### With Docker Compose (Recommended)

```bash
# Clone and enter the project
cd postal-code-genesis

# Set your Google Maps API key (optional)
export GOOGLE_MAPS_API_KEY=your_key_here

# Start all services
docker compose -f docker/docker-compose.yml up --build

# Seed demo data (South Sudan)
docker compose -f docker/docker-compose.yml exec backend python scripts/seed_demo.py
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432

### Without Docker (Local Development)

```bash
# 1. Start PostgreSQL with PostGIS
# Install PostGIS extension, create database "postal_genesis"

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
npm start

# 4. Seed demo data
cd backend
python scripts/seed_demo.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/countries` | Create country profile |
| GET | `/api/v1/countries` | List all countries |
| POST | `/api/v1/countries/{id}/analyze` | Analyze & get recommendations |
| POST | `/api/v1/countries/{id}/zones/auto-create` | Auto-generate postal zones |
| GET | `/api/v1/countries/{id}/zones` | List all zones |
| GET | `/api/v1/countries/{id}/stats` | Country statistics |
| POST | `/api/v1/countries/{id}/policy` | Generate policy documents |
| GET | `/api/v1/lookup/coordinates` | Lookup by GPS |
| GET | `/api/v1/lookup/search` | Search by name/landmark |
| POST | `/api/v1/lookup/ussd` | USSD/SMS lookup |
| GET | `/health` | Health check |

## Project Structure

```
postal-code-genesis/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # All API routes
│   │   ├── core/
│   │   │   ├── config.py          # Settings
│   │   │   └── database.py        # DB setup
│   │   ├── models/
│   │   │   ├── database.py        # SQLAlchemy models
│   │   │   └── schemas.py         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── country_setup_wizard.py   # Postal system designer
│   │   │   ├── zone_creation_engine.py   # Voronoi zone creation
│   │   │   ├── policy_generator.py       # Policy doc generator
│   │   │   └── public_lookup.py          # Lookup service
│   │   └── main.py               # FastAPI app
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.js
│   │   │   ├── CountryWizard.js
│   │   │   ├── CountryList.js
│   │   │   ├── ZoneMap.js
│   │   │   ├── LookupPanel.js
│   │   │   └── PolicyPanel.js
│   │   ├── services/api.js
│   │   ├── App.js
│   │   └── index.js
│   ├── public/index.html
│   └── package.json
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── scripts/
│   └── seed_demo.py
└── README.md
```

## Features

- **Country Setup Wizard** — Step-by-step guided setup for new countries
- **Intelligent Zone Creation** — Voronoi-based zones around settlements
- **Code Assignment** — Smart numbering with growth gaps
- **Policy Generator** — Government-ready policy documents
- **Public Lookup** — GPS, name search, and USSD/SMS
- **Interactive Map** — Zone visualization with Google Maps
- **Demo Data** — South Sudan (12 zones in Juba County)
