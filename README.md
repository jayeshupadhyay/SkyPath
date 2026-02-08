# SkyPath – Flight Itinerary Search

SkyPath is a full‑stack flight itinerary search prototype built as a take‑home assignment.  
It loads a static flight dataset, normalizes it on startup, and allows users to search for valid itineraries (direct, 1‑stop, and 2‑stop) while respecting real‑world connection rules and time zones.

The project is fully containerized and can be run with a single Docker command.

---

## 🚀 How to Run

### Prerequisites
- Docker Desktop (Windows / macOS / Linux)
- Docker Compose  
  > If `docker-compose` (hyphen) is not available on your system, use `docker compose` instead.

### Start the application
From the project root:

```bash
docker compose up
```

### Access the app
- **Frontend UI:** http://localhost:3000  
- **Backend API:** http://localhost:8000  
- **Health check:** http://localhost:8000/health

---

## 📁 Project Structure

```
.
├── backend
│   ├── app
│   │   └── main.py          # FastAPI application
│   ├── tests
│   │   └── test_api.py      # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend
│   ├── index.html           # UI markup
│   ├── styles.css           # UI styling
│   ├── app.js               # UI logic
│   └── Dockerfile
├── flights.json              # Provided dataset
├── docker-compose.yml
└── README.md
```

---

## 🧠 Architecture Overview

### Backend
- **Framework:** FastAPI (Python)
- **Data storage:** In‑memory (loaded from `flights.json` on startup)
- **Startup normalization:**
  - Invalid airport codes are dropped
  - Prices normalized to floats
  - Local timestamps are converted to timezone‑aware datetimes
  - UTC timestamps are precomputed
- **Indexes:** Flights are indexed by origin airport for fast lookup

### Frontend
- **Stack:** Vanilla HTML / CSS / JavaScript
- **Server:** Nginx (static files)
- **Features:**
  - Input validation
  - Loading / error / empty states
  - Preset test cases
  - Clear visualization of segments, layovers, duration, and price

### Docker
- `docker-compose.yml` runs:
  - Backend API on port `8000`
  - Frontend UI on port `3000`
- Dataset is mounted read‑only into the backend container

---

## ✈️ Search API

### Endpoint
```
GET /search?origin=JFK&destination=LAX&date=2024-03-15
```

### Parameters
- `origin`: 3‑letter IATA airport code
- `destination`: 3‑letter IATA airport code
- `date`: Travel date in `YYYY-MM-DD` format (interpreted in origin local time)

### Response (simplified)
```json
{
  "segments": [...],
  "layoversMinutes": [75],
  "totalDurationMinutes": 540,
  "totalPrice": 420.0
}
```

---

## 🔗 Connection Rules Implemented

- **Maximum stops:** 2 (up to 3 segments)
- **Minimum layover:**
  - 45 minutes for domestic connections
  - 90 minutes for international connections
- **Maximum layover:** 6 hours
- **Airport changes:** Not allowed (must connect at the same airport)
- **Time zones:** All calculations are done in UTC after normalization

Results are sorted by **total travel time (shortest first)**.

---

## 🧪 Tests

The backend includes a pytest suite covering:
- Health endpoint
- Valid searches (direct, domestic, international)
- Invalid inputs
- Edge cases (same origin/destination, date line crossing)

### Run tests (inside Docker)
```bash
docker compose exec backend pytest -q
```

---

## ✅ Test Cases from Instructions

The following instruction‑provided scenarios are supported and verified:

- JFK → LAX  
- SFO → NRT (international layovers)  
- BOS → SEA (connecting flights)  
- SYD → LAX (international date line)  
- Invalid airport codes  
- Same origin and destination  

---

## ⚖️ Tradeoffs & Design Decisions

- **No database:** Dataset is small and static; in‑memory storage keeps the system simple.
- **No caching:** Not needed at this scale.
- **No authentication:** Out of scope for the assignment.
- **Limited stops:** Capped at 2 for clarity, performance, and realism.

---

## 🔮 Future Improvements

With more time, the following could be added:
- Airport autocomplete in the UI
- Filtering (max stops, price cap)
- Pagination for large result sets
- Persistent storage and caching
- More extensive automated testing
- API schema documentation (OpenAPI examples)

---

## 📝 Notes

This project prioritizes correctness, clarity, and maintainability over premature optimization.  
All major logic is documented and structured to be easily extensible.

---

**Thank you for reviewing SkyPath!**
