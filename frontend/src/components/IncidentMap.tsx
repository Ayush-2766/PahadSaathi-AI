import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { ReportIntelligence } from "../api/client";

declare global { interface Window { L?: any } }
type Props = { reports: ReportIntelligence[] };

function loadLeaflet(): Promise<void> {
  if (window.L) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-leaflet="true"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Map library could not load")), { once: true });
      return;
    }
    if (!document.querySelector('link[data-leaflet-css="true"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      link.dataset.leafletCss = "true";
      document.head.appendChild(link);
    }
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.async = true;
    script.dataset.leaflet = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Map library could not load"));
    document.body.appendChild(script);
  });
}

export function IncidentMap({ reports }: Props) {
  const mapElement = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const searchMarkerRef = useRef<any>(null);
  const [mapError, setMapError] = useState("");
  const [searchText, setSearchText] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState("");
  const mappedReports = reports.filter(report =>
    typeof report.latitude === "number" && typeof report.longitude === "number"
    && Number.isFinite(report.latitude) && Number.isFinite(report.longitude)
  );
  const coordinateKey = mappedReports.map(r => r.report_id + r.latitude + r.longitude).join("|");

  useEffect(() => {
    let cancelled = false;
    let map: any;
    loadLeaflet().then(() => {
      if (cancelled || !mapElement.current || !window.L) return;
      const L = window.L;
      map = L.map(mapElement.current).setView([30.0668, 79.0193], 7);
      mapRef.current = map;
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(map);
      const markers: any[] = [];
      mappedReports.forEach(report => {
        const marker = L.marker([report.latitude, report.longitude]).addTo(map);
        const popup = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = report.village_name + ", " + report.district;
        const detail = document.createElement("p");
        detail.textContent = report.description;
        const severity = document.createElement("small");
        severity.textContent = "Severity: " + report.severity.recommended_severity + " · Status: " + report.status;
        popup.append(title, detail, severity);
        marker.bindPopup(popup);
        markers.push(marker);
      });
      if (markers.length === 1) map.setView(markers[0].getLatLng(), 13);
      if (markers.length > 1) map.fitBounds(L.featureGroup(markers).getBounds().pad(0.18));
      window.setTimeout(() => map?.invalidateSize(), 150);
    }).catch(() => setMapError("मानचित्र लोड नहीं हो सका। इंटरनेट कनेक्शन जाँचें और पेज रीफ्रेश करें।"));
    return () => { cancelled = true; mapRef.current = null; if (map) map.remove(); };
  }, [coordinateKey]);

  async function findLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchText.trim();
    if (!query) { setSearchMessage("गांव, जिला या स्थान का नाम लिखें।"); return; }
    setSearching(true);
    setSearchMessage("स्थान खोजा जा रहा है…");
    try {
      const params = new URLSearchParams({ q: query + ", Uttarakhand, India", format: "jsonv2", limit: "1", countrycodes: "in" });
      const response = await fetch("https://nominatim.openstreetmap.org/search?" + params.toString(), {
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error("search");
      const results = await response.json();
      if (!results.length) { setSearchMessage("स्थान नहीं मिला। गांव के साथ जिला लिखकर खोजें।"); return; }
      const place = results[0];
      const lat = Number(place.lat);
      const lon = Number(place.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || !mapRef.current || !window.L) throw new Error("map");
      mapRef.current.setView([lat, lon], 14);
      if (searchMarkerRef.current) searchMarkerRef.current.remove();
      searchMarkerRef.current = window.L.marker([lat, lon]).addTo(mapRef.current);
      searchMarkerRef.current.bindPopup(String(place.display_name)).openPopup();
      setSearchMessage("स्थान मिल गया: " + String(place.display_name));
    } catch {
      setSearchMessage("स्थान खोजने में समस्या हुई। इंटरनेट कनेक्शन जाँचकर फिर कोशिश करें।");
    } finally {
      setSearching(false);
    }
  }

  return <section className="command-section incident-map-section">
    <div className="section-heading"><div><p className="eyebrow">GPS-आधारित घटना स्थान</p><h3>उत्तराखंड घटना मानचित्र</h3></div><p>{mappedReports.length} स्थान मैप किए गए</p></div>
    <p className="map-disclaimer">रिपोर्ट के GPS मार्कर और गांव/जिला नाम से खोजे गए स्थान अलग-अलग दिखाए जाते हैं। खोजा गया स्थान रिपोर्ट का पुष्ट GPS स्थान नहीं है।</p>
    <form className="map-search" onSubmit={findLocation}>
      <input value={searchText} onChange={event => setSearchText(event.target.value)} placeholder="गांव या जिला खोजें — जैसे Joshimath, Chamoli" aria-label="गांव या जिला खोजें" />
      <button type="submit" disabled={searching}>{searching ? "खोज रहे हैं…" : "मानचित्र पर खोजें"}</button>
    </form>
    {searchMessage && <p className="map-search-message" role="status">{searchMessage}</p>}
    <div ref={mapElement} className="incident-map" role="application" aria-label="GPS incident map of Uttarakhand" />
    {mapError && <p className="dashboard-error">{mapError}</p>}
    {!mappedReports.length && <p className="map-empty">अभी किसी रिपोर्ट में GPS निर्देशांक नहीं हैं। नागरिक रिपोर्ट में GPS जोड़ने पर घटना का वास्तविक मार्कर यहां दिखेगा। गांव नाम से खोजने पर केवल स्थान देखा जा सकता है; उसे रिपोर्ट का GPS नहीं माना जाएगा।</p>}
  </section>;
}
