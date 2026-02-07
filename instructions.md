# SkyPath: Flight Connection Search Engine

## Take-Home Engineering Challenge

**Time Budget:** 4-6 hours, although you may spend as long as you'd like | **Stack:** Your choice (Backend + Frontend required)

---

## Overview

You're building a prototype flight connection search engine for a travel startup. Given a dataset of flight schedules, users should be able to search for valid flight itineraries between two airports, including multi-stop connections.

---

## Requirements

### Backend Service (REST or GraphQL API)

1. **Load the provided `flights.json` dataset on startup**

2. **Implement a search endpoint** accepting:
   - `origin` — 3-letter IATA airport code (e.g., `JFK`)
   - `destination` — 3-letter IATA airport code (e.g., `LAX`)
   - `date` — ISO 8601 format (`YYYY-MM-DD`)

3. **Return valid itineraries** including:
   - Direct flights
   - 1-stop connections
   - 2-stop connections (maximum)
   
4. **Each itinerary must include:**
   - List of flight segments with flight numbers, times, airports
   - Layover durations at each connection point
   - Total travel duration
   - Total price

5. **Sort results by total travel time** (shortest first)

---

### Connection Rules

| Rule | Requirement |
|------|-------------|
| **Minimum layover (domestic)** | 45 minutes |
| **Minimum layover (international)** | 90 minutes |
| **Maximum layover** | 6 hours |
| **Airport changes** | Passengers cannot change airports during a layover (e.g., JFK→LGA is not valid) |
| **Time zones** | All times in the dataset are in **local airport time**—you must account for time zones when calculating durations |

**Domestic vs International:**
- A connection is "domestic" if both the arriving and departing flights are within the **same country**
- Use the `country` field in the airports data to determine this
- Example: JFK→ORD→LAX = domestic (all US). JFK→LHR→CDG = international.

---

### Frontend Service

1. **Search form** with:
   - Origin airport input
   - Destination airport input
   - Date picker

2. **Results display** showing:
   - Flight segments with times and airports
   - Layover information
   - Total duration and price

3. **User experience:**
   - Input validation with clear error messages
   - Loading state while searching
   - Empty state when no results found
   - Handle and display API errors gracefully

---

### Infrastructure

1. **Provide a `docker-compose.yml`** that starts both services with:
   ```bash
   docker-compose up
   ```
   
2. **Include a `README.md`** documenting:
   - How to run the application
   - Architecture decisions and why you made them
   - Tradeoffs you considered
   - What you would improve with more time

3. **Commit history should reflect your development process**
   - Do NOT squash into a single commit
   - We want to see how you work

---

## Dataset

The `flights.json` file contains:

```json
{
  "airports": [
    {
      "code": "JFK",
      "name": "John F. Kennedy International",
      "city": "New York",
      "country": "US",
      "timezone": "America/New_York"
    }
  ],
  "flights": [
    {
      "flightNumber": "SP101",
      "airline": "SkyPath Airways",
      "origin": "JFK",
      "destination": "LAX",
      "departureTime": "2024-03-15T08:30:00",
      "arrivalTime": "2024-03-15T11:45:00",
      "price": 299.00,
      "aircraft": "A320"
    }
  ]
}
```

**Important notes about the data:**
- Times are in local airport time (use the `timezone` field)
- The dataset covers flights on `2024-03-15` and some overnight flights landing on `2024-03-16`
- ~260 flights across 25 airports worldwide

---

## Test Cases

Use these to verify your implementation:

| # | Search | Expected Behavior |
|---|--------|-------------------|
| 1 | `JFK → LAX, 2024-03-15` | Returns direct flights AND multi-stop options |
| 2 | `SFO → NRT, 2024-03-15` | International route—90-minute minimum layover applies |
| 3 | `BOS → SEA, 2024-03-15` | No direct flight exists—must find connections |
| 4 | `JFK → JFK, 2024-03-15` | Should return empty results or validation error |
| 5 | `XXX → LAX, 2024-03-15` | Invalid airport code—graceful error handling |
| 6 | `SYD → LAX, 2024-03-15` | Date line crossing—arrival appears "before" departure in local time |

---

## Evaluation Criteria

| Category | Weight | What We're Looking For |
|----------|--------|------------------------|
| **Correctness** | 30% | Connection rules implemented precisely; timezone handling correct; edge cases covered |
| **Code Quality** | 25% | Clean architecture, appropriate abstractions, consistent style |
| **Problem Solving** | 20% | Efficient algorithm; handles data quirks gracefully |
| **Documentation** | 15% | Clear README; architecture rationale; honest tradeoff assessment |
| **Polish & Passion** | 10% | Tests, thoughtful UX, creative additions |

---

## Submission

1. Push your code to a **public GitHub repository**

2. Ensure we can run the application with:
   ```bash
   git clone <your-repo>
   cd <your-repo>
   docker-compose up
   ```

3. Email the repository link to us

4. **Do not squash your commits**—we want to see your development process

---

## FAQ

### Can I use AI tools (Copilot, ChatGPT, Claude)?

Yes. We assume you will. We're evaluating:
- The quality of the final result
- Your ability to critically assess and refine AI-generated code
- Your understanding of what you've built (we'll ask in the interview)

### What if I can't finish in 6 hours?

Submit what you have. Document what's incomplete and what you'd do next in your README. 

Optional: You are also welcome to spend as much time as you like, just let us know. 

### What tech stack should I use?

Whatever you're most productive in.

### Should I deploy this somewhere?

Not required. Local Docker setup is sufficient. If you choose to deploy, that's a nice bonus but don't sacrifice code quality for it.

### Can I add features beyond the requirements?

Yes, but prioritize correctness first.

### What if I have questions about the requirements?

Make reasonable assumptions and document them in your README. We're also evaluating your judgment when requirements are ambiguous.

### How will the interview work?

After submission, we'll:
1. Review your code
2. Run the test cases
3. Schedule a 60 minute call to discuss your approach, walk through specific code sections, and ask follow-up questions

---

## Getting Started

1. Download the `flights.json` dataset (attached)

2. Set up your project structure:
   ```
   skypath/
   ├── backend/
   │   ├── Dockerfile
   │   └── ...
   ├── frontend/
   │   ├── Dockerfile
   │   └── ...
   ├── docker-compose.yml
   ├── flights.json
   └── README.md
   ```

3. Build your services

4. Test, iterate

5. Write your README last, when you can reflect on the whole project

---

Good luck! We're excited to see what you build.
