/**
 * NYC Apartment Cost Viewer – scrollable map with heatmap + markers.
 * Loads data/listings.json (generate via scripts/prepare_data.py from assignmentStuff/NY-House-Dataset-5boroughs.csv).
 */

const NYC_CENTER = [40.7128, -74.006];
const NYC_ZOOM = 11;

/* Heatmap gradient: cream → dollar green (paper style, matches lighter green) */
const HEAT_GRADIENT = {
  0.0: "rgba(242, 237, 228, 0)",
  0.3: "rgba(93, 138, 88, 0.4)",
  0.6: "rgba(61, 74, 60, 0.65)",
  1.0: "rgba(53, 64, 50, 0.9)",
};

let map;
let heatLayer;
let markerLayer;
let listings = [];

function formatPrice(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function median(arr) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function buildHeatPoints() {
  const valid = listings.filter((l) => l.price != null && l.price > 0);
  if (!valid.length) return [];
  const maxPrice = Math.max(...valid.map((l) => l.price));
  const minPrice = Math.min(...valid.map((l) => l.price));
  const range = maxPrice - minPrice || 1;
  return valid.map((l) => [l.lat, l.lng, (l.price - minPrice) / range]);
}

function createMarkerIcon() {
  return L.divIcon({
    className: "marker-pin",
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function popupContent(listing) {
  const parts = [];
  if (listing.price != null) parts.push(`<span class="popup-price">${formatPrice(listing.price)}</span>`);
  if (listing.address) parts.push(listing.address);
  if (listing.zip) parts.push(`ZIP ${listing.zip}`);
  if (listing.beds != null) parts.push(`${listing.beds} bed`);
  if (listing.baths != null) parts.push(`${listing.baths} bath`);
  if (listing.type) parts.push(listing.type);
  return parts.join(" · ") || "—";
}

function updateSideCard(listing) {
  const el = document.getElementById("listingContent");
  if (!listing) {
    el.textContent = "Select a marker";
    return;
  }
  const lines = [];
  if (listing.price != null) lines.push(`Price: ${formatPrice(listing.price)}`);
  if (listing.address) lines.push(listing.address);
  if (listing.zip) lines.push(`ZIP: ${listing.zip}`);
  if (listing.beds != null) lines.push(`Beds: ${listing.beds}`);
  if (listing.baths != null) lines.push(`Baths: ${listing.baths}`);
  if (listing.type) lines.push(`Type: ${listing.type}`);
  el.innerHTML = lines.join("<br/>");
}

function initMap() {
  // Stable container: ensure map has dimensions before init
  const mapEl = document.getElementById("map");
  mapEl.style.height = "100%";
  mapEl.style.width = "100%";

  map = L.map("map", {
    center: NYC_CENTER,
    zoom: NYC_ZOOM,
    scrollWheelZoom: false,
    zoomSnap: 0,
    zoomDelta: 0.5,
    butterSmoothZoom: true,
    butterSmoothScale: 0.0025,
    butterSmoothEasing: 0.28,
    butterSmoothEndDelay: 180,
    butterSmoothZoomAnimationDuration: 0.2,
  });

  // Subtle base – no bright tiles; use a light style that fits beige theme
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png", {
    attribution: "",
    maxZoom: 19,
  }).addTo(map);
  map.removeControl(map.attributionControl);

  // Heatmap – cream-to-green gradient (paper style)
  const points = buildHeatPoints();
  heatLayer = L.heatLayer(points, {
    radius: 28,
    blur: 20,
    maxZoom: 16,
    minOpacity: 0.35,
    max: 1,
    gradient: HEAT_GRADIENT,
  });
  if (document.getElementById("toggleHeatmap").checked) map.addLayer(heatLayer);

  // Markers – start hidden to avoid lag with many listings
  markerLayer = L.layerGroup();
  if (document.getElementById("toggleMarkers").checked) map.addLayer(markerLayer);
  listings.forEach((listing) => {
    const marker = L.marker([listing.lat, listing.lng], { icon: createMarkerIcon() });
    marker.bindPopup(popupContent(listing), { className: "card-panel" });
    marker.listing = listing;
    marker.on("click", () => updateSideCard(listing));
    markerLayer.addLayer(marker);
  });

  // Toggles
  document.getElementById("toggleHeatmap").addEventListener("change", (e) => {
    if (e.target.checked) map.addLayer(heatLayer);
    else map.removeLayer(heatLayer);
  });
  document.getElementById("toggleMarkers").addEventListener("change", (e) => {
    if (e.target.checked) map.addLayer(markerLayer);
    else map.removeLayer(markerLayer);
  });

  // Stats (listings.json is already filtered to 5 boroughs by prepare_data.py)
  const prices = listings.map((l) => l.price).filter((p) => p != null && p > 0);
  document.getElementById("statCount").textContent = listings.length.toLocaleString();
  document.getElementById("statPrice").textContent = formatPrice(median(prices));

  // Ensure map fills container after layout (prevents jump on first interaction)
  requestAnimationFrame(() => {
    map.invalidateSize();
  });
}

async function loadData() {
  try {
    const res = await fetch("data/listings.json");
    if (!res.ok) throw new Error(res.statusText);
    listings = await res.json();
  } catch (e) {
    console.error("Failed to load data/listings.json:", e);
    document.getElementById("listingContent").innerHTML =
      "No data. Run: <code>python scripts/prepare_data.py</code> (uses <code>assignmentStuff/NY-House-Dataset-5boroughs.csv</code>).";
    document.getElementById("statCount").textContent = "0";
    document.getElementById("statPrice").textContent = "—";
    return;
  }
  if (listings.length) initMap();
  else {
    document.getElementById("listingContent").textContent = "No listings in 5 boroughs.";
    document.getElementById("statCount").textContent = "0";
    document.getElementById("statPrice").textContent = "—";
  }
}

loadData();
