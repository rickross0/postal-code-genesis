# 📍 PostalCode Genesis — Complete User Guide

> **Building Addresses Where None Exist**
>
> A step-by-step guide to designing, generating, and deploying postal code systems for countries and regions that lack formal addressing infrastructure.

---

## Table of Contents

1. [What This Platform Does](#what-this-platform-does)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Docker Compose)](#quick-start-docker-compose)
4. [Step-by-Step Walkthrough](#step-by-step-walkthrough)
   - Step 1: Create a Country Profile
   - Step 2: Analyze & Get Recommendations
   - Step 3: Auto-Generate Postal Zones
   - Step 4: Explore the Zone Map
   - Step 5: Lookup Postal Codes
   - Step 6: Generate Policy Documents
5. [Using the API Directly](#using-the-api-directly)
6. [Seeding Demo Data](#seeding-demo-data)
7. [Deploying to Render.com](#deploying-to-rendercom)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## What This Platform Does

PostalCode Genesis is an end-to-end platform for creating postal code systems from scratch. It is designed for:

- **Developing nations** without formal street addressing
- **Post-conflict regions** where infrastructure has been disrupted
- **Rural areas** where landmarks matter more than street names
- **Government agencies** and **NGOs** digitizing geographic identity

The platform handles everything from system design (code format, hierarchy, cost estimates) to algorithmic zone generation, public lookup services, and printable government policy documents.

---

## Prerequisites

Before you begin, ensure you have:

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 20.10+ | Runs PostgreSQL + PostGIS, backend, and frontend |
| Docker Compose | 2.0+ | Orchestrates multi-container setup |
| Git | 2.30+ | Clones the repository |
| (Optional) Google Maps API Key | — | Enables interactive map rendering |

### Check your environment

```bash
docker --version
docker compose version
git --version
```

---

## Quick Start (Docker Compose)

### 1. Clone the repository

```bash
git clone https://github.com/rickross0/postal-code-genesis.git
cd postal-code-genesis
```

### 2. Set environment variables (optional)

If you have a Google Maps API key, export it so maps render in the frontend:

```bash
export GOOGLE_MAPS_API_KEY="your_key_here"
```

> Without a key, the map falls back to a clean card-based zone list — the platform still works fully.

### 3. Start all services

```bash
docker compose up --build
```

This command builds and starts three services:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | React web application |
| **Backend API** | http://localhost:8000 | FastAPI server |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger documentation |
| **Database** | localhost:5432 | PostgreSQL + PostGIS |

Wait for the health checks to pass (the backend waits for the database to be ready).

### 4. Seed demo data (optional)

To explore the platform with pre-loaded South Sudan data:

```bash
docker compose exec backend python scripts/seed_demo.py
```

This creates:
- 1 country (South Sudan)
- 10 regions (states)
- 6 districts (Central Equatoria counties)
- 12 postal zones (Juba County)
- 10 landmarks

---

## Step-by-Step Walkthrough

### Step 1: Create a Country Profile

1. Open the frontend at **http://localhost:3000**
2. The sidebar on the left shows navigation. Click **🌍 Country Setup**.
3. Fill in the country profile form:

| Field | Example Value | Why It Matters |
|-------|---------------|----------------|
| **Country Name** | South Sudan | Display name |
| **ISO Code** | SSD | 2–3 letter country identifier |
| **Tier** | Mixed Rural/Urban | Determines zone density and code complexity |
| **Population** | 11,000,000 | Drives how many zones are needed |
| **Area (km²)** | 619,745 | Affects zone size calculations |
| **Regions** | 10 | Top-level administrative divisions |
| **Districts** | 79 | Mid-level divisions |
| **Languages** | English, Arabic | Used for localized terminology in policy docs |
| **Urban %** | 19.6 | Rural populations get larger zones |
| **Literacy Rate %** | 34 | Low literacy triggers simple numeric-only codes |
| **Mobile Penetration %** | 33 | Above 30% enables USSD/SMS lookup recommendations |
| **Has street names** | ☐ Unchecked | Tells the system zones must be small enough to work without street addresses |

4. Click **Create Country Profile →**
5. The wizard advances to **Step 2** and shows your created country.

> **Tip:** For a first test, use South Sudan's real stats (population ~11M, area ~620k km², 10 states, 79 counties). This gives realistic zone recommendations.

---

### Step 2: Analyze & Get Recommendations

1. In **Step 2: System Analysis**, click **Analyze Country →**
2. The platform runs the `PostalSystemDesigner` algorithm and displays:

**Code Format Recommendation**
- Format: `RR-DD-ZZ` (e.g., `01-01-03`)
- Total capacity: ~970,299 zones
- Estimated zones needed: ~2,200

**Metrics**
- People per zone target
- Implementation timeline (months)
- Estimated total cost in USD

**Special Considerations**
These are contextual warnings and actions based on your inputs. Examples:
- *"No street names exist"* → Make zones small; use landmark-based sub-addressing
- *"Low literacy rate"* → Use simple numeric codes; consider color-coding
- *"Mobile phones available"* → Build USSD/SMS lookup
- *"Primarily rural population"* → Map landmarks during zone creation
- *"Post-conflict / unstable areas"* → Reserve 50% of codes for future growth

> **Key insight:** The system adapts its recommendations to your country's reality. A Tier 4 post-conflict country gets a different code structure than a Tier 1 urban developing country.

---

### Step 3: Auto-Generate Postal Zones

1. In **Step 3: Recommendations**, click **Auto-Create Zones →**
2. The `ZoneCreationEngine` algorithmically generates zones using:
   - **Voronoi tessellation** (if settlement data exists)
   - **Grid fallback** (if no settlement data)
3. The system assigns postal codes automatically using the recommended format.

**What happens under the hood:**
- A default region (`Region 01`) and district (`District 01`) are created if they don't exist
- Zones are carved using geometry algorithms
- Each zone gets a unique code (e.g., `01-01-01`, `01-01-02`, `01-01-03`)
- Codes are spaced apart to reserve room for future expansion

4. The wizard shows **✓ Complete** when finished.

---

### Step 4: Explore the Zone Map

1. In the sidebar, click **🗺️ Zone Map**
2. Select your country from the sidebar list (e.g., **South Sudan**)
3. The map view opens:

**With Google Maps API Key:**
- Interactive Google Map centered on the country
- Colored circles show each postal zone
- Click any marker to see zone details

**Without API Key (Fallback):**
- Clean card-based grid listing all zones
- Each card shows: postal code, zone name, population
- Click a card to open the info panel

**Info Panel Shows:**
- Postal code (large, colored)
- Zone name
- Region and district names
- Population estimate
- Area in km²
- Status (active / proposed / inactive)

> **Refresh:** Click the **Refresh** button in the toolbar to reload zones after making changes via the API.

---

### Step 5: Lookup Postal Codes

1. In the sidebar, click **🔍 Lookup**
2. Two search methods are available:

#### A. Lookup by GPS Coordinates
- Enter **Latitude** and **Longitude**
- Click **Find Code**
- The system queries PostGIS to find which zone polygon contains that point
- If outside all zones, it shows the **nearest zone** with distance

**Example coordinates (Juba, South Sudan):**
- Lat: `4.85`
- Lng: `31.6`

**Result:**
```
01-01-01
Zone: Juba Central Market Area
District: Juba County
Region: Central Equatoria
```

#### B. Search by Name
- Enter a place name or landmark (e.g., `Juba Market`, `University`, `Hospital`)
- Enter the country ISO code (e.g., `SSD`)
- Click **Search**

**Result:**
- Matching zones with postal codes
- Matching landmarks with categories

> **How it works:** Uses PostgreSQL's `pg_trgm` (trigram) similarity search for fuzzy name matching. Searching `Juba` will match `Juba Central Market`, `Juba University`, etc.

---

### Step 6: Generate Policy Documents

1. In the sidebar, click **📄 Policy Docs**
2. Select a country from the sidebar (or ensure one is selected)
3. Click **Generate Policy for [Country Name]**
4. Two documents are produced:

#### Policy Document
A formal government-ready document including:
- **Section 1:** Purpose and scope
- **Section 2:** Code structure and format breakdown
- **Section 3:** Administrative hierarchy
- **Section 4:** Governance rules
- **Section 5:** Implementation phases with timelines
- **Section 6:** Maintenance and update rules
- **Section 7:** Public access commitments

#### Implementation Guide
A practical step-by-step checklist:
- Stakeholder engagement (Week 1–4)
- Data gathering (Week 2–8)
- System design (Week 4–12)
- Field verification (Week 8–20)
- Finalization (Week 16–24)
- Launch (Week 20–28)
- Ongoing maintenance

> **Use case:** Print these documents and present them to a Ministry of Communications, postal authority, or donor agency as the official implementation plan.

---

## Using the API Directly

The backend exposes a full REST API. You can interact with it via `curl`, Postman, or any HTTP client.

### Base URL
```
http://localhost:8000/api/v1
```

### 1. Create a Country

```bash
curl -X POST http://localhost:8000/api/v1/countries \
  -H "Content-Type: application/json" \
  -d '{
    "name": "South Sudan",
    "iso_code": "SSD",
    "tier": "mixed_rural_urban",
    "estimated_population": 11000000,
    "area_sq_km": 619745,
    "num_regions": 10,
    "num_districts": 79,
    "languages": ["English", "Arabic"],
    "has_street_names": false,
    "urban_percentage": 19.6,
    "literacy_rate": 0.34,
    "mobile_penetration": 0.33
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "South Sudan",
  "iso_code": "SSD",
  "tier": "mixed_rural_urban",
  "estimated_population": 11000000,
  ...
}
```

### 2. Analyze a Country

```bash
curl -X POST http://localhost:8000/api/v1/countries/1/analyze
```

**Response includes:**
- Recommended code format (`RR-DD-ZZ`)
- Estimated total zones
- Implementation timeline
- Cost breakdown
- Special considerations

### 3. Auto-Create Zones

```bash
curl -X POST "http://localhost:8000/api/v1/countries/1/zones/auto-create?region_code=01&district_code=01&target_population=5000"
```

**Response:** Array of generated zones with postal codes, centers, and areas.

### 4. List All Zones

```bash
curl http://localhost:8000/api/v1/countries/1/zones
```

### 5. Lookup by Coordinates

```bash
curl "http://localhost:8000/api/v1/lookup/coordinates?lat=4.85&lng=31.6"
```

### 6. Search by Name

```bash
curl "http://localhost:8000/api/v1/lookup/search?query=Juba%20Market&country=SSD"
```

### 7. Generate Policy Document

```bash
curl -X POST http://localhost:8000/api/v1/countries/1/policy
```

### 8. Health Check

```bash
curl http://localhost:8000/health
```

> **Interactive docs:** Visit http://localhost:8000/docs for Swagger UI with all endpoints, request schemas, and try-it-now functionality.

---

## Seeding Demo Data

If you want to explore with realistic data without manually creating everything:

```bash
docker compose exec backend python scripts/seed_demo.py
```

**What gets seeded:**

| Entity | Count | Details |
|--------|-------|---------|
| Country | 1 | South Sudan (SSD), post-conflict tier |
| Regions | 10 | All 10 states of South Sudan |
| Districts | 6 | Central Equatoria counties (Juba, Yei, etc.) |
| Zones | 12 | Juba County postal zones with realistic populations |
| Landmarks | 10 | Markets, hospitals, schools, churches, airport |

After seeding, go to **🗺️ Zone Map** → select **South Sudan** to see live data.

---

## Deploying to Render.com

The repository includes a `render.yaml` blueprint for one-click cloud deployment.

### Steps

1. **Push your code to GitHub** (already done if you cloned this repo)
2. Go to [dashboard.render.com](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Select your `postal-code-genesis` repository
5. Render automatically creates two services:
   - `postal-genesis-db` — Private PostGIS database
   - `postal-genesis` — Combined backend + frontend web service
6. (Optional) Set `GOOGLE_MAPS_API_KEY` in the web service environment variables
7. Click **Apply**

After deployment, your app is live at:
```
https://postal-genesis-xxxx.onrender.com
```

**How Render deployment works:**
- `Dockerfile.render` is a multi-stage build
- Stage 1: Node builds the React frontend
- Stage 2: Python FastAPI serves the built frontend as static files
- PostGIS runs as a private service; the backend connects via auto-injected `DB_HOST`/`DB_PORT`
- `POSTGRES_PASSWORD` is auto-generated by Render

---

## Troubleshooting

### Issue: `docker compose up` fails with database connection errors

**Solution:** The backend waits for the database healthcheck, but on first run the database may take longer to initialize PostGIS. Wait 30 seconds and restart:

```bash
docker compose down
docker compose up
```

### Issue: `asyncpg` timezone error when creating countries

**Solution:** This was a known bug where `datetime.now(timezone.utc)` (offset-aware) was rejected by `asyncpg` for `TIMESTAMP WITHOUT TIME ZONE` columns. Ensure you are on the latest commit where this is fixed.

### Issue: Google Maps doesn't load

**Solution:** Check that `REACT_APP_GOOGLE_MAPS_API_KEY` is set. Without a key, the platform falls back to a card-based zone list — all functionality still works.

### Issue: `similarity()` function not found during name search

**Solution:** The `pg_trgm` extension must be enabled in PostgreSQL. The `init_db()` function does this automatically, but if you manually created the database, run:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Issue: `ModuleNotFoundError: No module named 'pyproj'`

**Solution:** Install dependencies from `requirements.txt`:

```bash
pip install -r backend/requirements.txt
```

---

## Best Practices

1. **Start with demo data** — Seed South Sudan to understand the data model before creating your own country.
2. **Use realistic population figures** — The zone density algorithm depends heavily on population. Underestimating population leads to oversized zones.
3. **Reserve codes for growth** — The auto-generator only uses ~70% of available codes, leaving room for urban expansion and new settlements.
4. **Verify zones in the field** — Algorithmic zones are a starting point. Send field workers with the mobile-friendly web app to verify boundaries and collect landmarks.
5. **Export policy documents early** — Share the auto-generated policy document with government stakeholders to build political support before zone finalization.
6. **Enable USSD if mobile penetration is high** — The platform recommends this automatically, but you must configure a USSD gateway provider (e.g., Africa's Talking, Twilio) in production.
7. **Back up the PostGIS database** — Zone boundaries are geometries; treat them as valuable infrastructure data. Render provides automated backups for paid plans.
8. **Iterate on zone boundaries** — Populations shift. The platform supports zone status changes (`active`, `proposed`, `inactive`) and allows splitting/merging as demographics change.

---

## Summary

| Task | Where to Do It |
|------|----------------|
| Add a new country | 🌍 Country Setup wizard |
| See code recommendations | Step 2 in wizard ( Analyze Country ) |
| Generate zones | Step 3 in wizard ( Auto-Create Zones ) |
| View zones visually | 🗺️ Zone Map |
| Find a postal code | 🔍 Lookup panel or API |
| Get government documents | 📄 Policy Docs panel |
| Explore the API | http://localhost:8000/docs |

---

**Need help?** Check the API docs at `/docs`, review the code in `backend/app/services/`, or seed the demo data and experiment with South Sudan as your reference implementation.
