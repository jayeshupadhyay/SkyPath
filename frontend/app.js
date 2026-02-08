// Works whether your host is localhost or something else
const API_BASE = `${location.protocol}//${location.hostname}:8000`;

const originEl = document.getElementById("origin");
const destEl = document.getElementById("destination");
const dateEl = document.getElementById("date");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const resultsNoteEl = document.getElementById("resultsNote");
const btn = document.getElementById("searchBtn");
const swapBtn = document.getElementById("swapBtn");
const apiBaseEl = document.getElementById("apiBase");

const healthDot = document.getElementById("healthDot");
const healthText = document.getElementById("healthText");

apiBaseEl.textContent = API_BASE;

function minutesToHhMm(mins) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h}h ${m}m`;
}

function showStatus(text, type = "info") {
  statusEl.style.display = "block";
  statusEl.className = "msg " + (type === "ok" ? "ok" : "");
  statusEl.textContent = text;
}

function hideStatus() {
  statusEl.style.display = "none";
  statusEl.textContent = "";
  statusEl.className = "msg";
}

function showError(text) {
  errorEl.style.display = "block";
  errorEl.textContent = text;
}

function hideError() {
  errorEl.style.display = "none";
  errorEl.textContent = "";
}

function setLoading(isLoading) {
  btn.disabled = isLoading;
  btn.textContent = isLoading ? "Searching…" : "Search";
}

function normalizeIata(v) {
  return (v || "").trim().toUpperCase().slice(0, 3);
}

function validateInputs(origin, destination, date) {
  const iata = /^[A-Z]{3}$/;
  if (!iata.test(origin)) return "Origin must be a 3-letter IATA code (e.g., JFK).";
  if (!iata.test(destination)) return "Destination must be a 3-letter IATA code (e.g., LAX).";
  if (origin === destination) return "Origin and destination must be different.";
  if (!date) return "Please select a date.";
  return null;
}

function routeString(segments) {
  if (!segments || segments.length === 0) return "";
  const codes = [segments[0].origin];
  segments.forEach(s => codes.push(s.destination));
  return codes.join(" → ");
}

// Input is ISO with offset like "2024-03-15T08:30:00-04:00".
function prettyLocal(isoWithOffset) {
  // Show YYYY-MM-DD HH:MM (UTC±hh:mm)
  const m = String(isoWithOffset).match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):\d{2}([+-]\d{2}:\d{2})/);
  if (!m) return isoWithOffset;
  const [, d, t, off] = m;
  return `${d} ${t} (UTC${off})`;
}

function renderResults(itins) {
  resultsEl.innerHTML = "";

  if (!itins || itins.length === 0) {
    resultsEl.innerHTML = `<div class="panel" style="margin-top:12px;">No results found.</div>`;
    resultsNoteEl.textContent = "0 itineraries";
    return;
  }

  resultsNoteEl.textContent = `${itins.length} itineraries`;

  itins.forEach((itin, idx) => {
    const card = document.createElement("div");
    card.className = "card";

    const stops = Math.max(0, itin.segments.length - 1);

    const top = document.createElement("div");
    top.className = "cardTop";
    top.innerHTML = `
      <div class="route">${routeString(itin.segments)}</div>
      <div class="metaPills">
        <span class="pill">#<strong>${idx + 1}</strong></span>
        <span class="pill"><strong>${stops}</strong> stop(s)</span>
        <span class="pill">Total <strong>${minutesToHhMm(itin.totalDurationMinutes)}</strong></span>
        <span class="pill">Price <strong>$${Number(itin.totalPrice).toFixed(2)}</strong></span>
      </div>
    `;
    card.appendChild(top);

    const segWrap = document.createElement("div");
    segWrap.className = "segments";

    itin.segments.forEach((s, i) => {
      const seg = document.createElement("div");
      seg.className = "seg";
      seg.innerHTML = `
        <div class="segHead">
          <div class="segTitle">${s.origin} → ${s.destination}</div>
          <div class="segSub">${s.flightNumber} · ${s.airline} · ${s.aircraft}</div>
        </div>
        <div class="times">
          <div>Dep: <code>${prettyLocal(s.departureTimeLocal)}</code></div>
          <div>Arr: <code>${prettyLocal(s.arrivalTimeLocal)}</code></div>
        </div>
      `;
      segWrap.appendChild(seg);

      if (i < itin.layoversMinutes.length) {
        const lay = document.createElement("div");
        lay.className = "layover";
        lay.innerHTML = `Layover: <strong>${minutesToHhMm(itin.layoversMinutes[i])}</strong>`;
        segWrap.appendChild(lay);
      }
    });

    card.appendChild(segWrap);
    resultsEl.appendChild(card);
  });
}

async function checkHealth() {
  try {
    const r = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    if (!r.ok) throw new Error("bad status");
    const data = await r.json();
    healthDot.classList.add("ok");
    healthText.textContent = `Backend OK · ${data.airports} airports · ${data.flights} flights`;
  } catch (e) {
    healthDot.classList.remove("ok");
    healthText.textContent = "Backend unreachable";
  }
}

async function doSearch() {
  hideError();

  const origin = normalizeIata(originEl.value);
  const destination = normalizeIata(destEl.value);
  const d = dateEl.value;

  originEl.value = origin;
  destEl.value = destination;

  const validationError = validateInputs(origin, destination, d);
  if (validationError) {
    showError(validationError);
    return;
  }

  setLoading(true);
  showStatus("Searching itineraries…");

  try {
    const url = `${API_BASE}/search?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&date=${encodeURIComponent(d)}`;
    const resp = await fetch(url, { cache: "no-store" });

    if (!resp.ok) {
      let detail = `API error (${resp.status})`;
      try {
        const err = await resp.json();
        if (err && err.detail) detail = err.detail;
      } catch (_) {}
      throw new Error(detail);
    }

    const data = await resp.json();
    renderResults(data);

    if (!data || data.length === 0) {
      showStatus("No itineraries found for that route/date.");
    } else {
      showStatus(`Found ${data.length} itineraries.`, "ok");
    }
  } catch (e) {
    resultsEl.innerHTML = "";
    resultsNoteEl.textContent = "—";
    hideStatus();
    showError(e.message || "Unknown error");
  } finally {
    setLoading(false);
  }
}

// Enter to search from any input
[originEl, destEl, dateEl].forEach(el => {
  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch();
  });
});

swapBtn.addEventListener("click", () => {
  const a = originEl.value;
  originEl.value = destEl.value;
  destEl.value = a;
});

// Search button
btn.addEventListener("click", doSearch);

// Preset test cases
document.querySelectorAll("[data-preset]").forEach(b => {
  b.addEventListener("click", () => {
    const [o, d, dt] = b.getAttribute("data-preset").split(",");
    originEl.value = o;
    destEl.value = d;
    dateEl.value = dt;
    doSearch();
  });
});

// Defaults for quick demo
originEl.value = "JFK";
destEl.value = "LAX";
dateEl.value = "2024-03-15";

checkHealth();
