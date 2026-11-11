import { useEffect, useRef, useState } from "react";
import type { ReportIntelligence } from "../api/client";

declare global {
  interface Window { L?: any }
}

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
  const [mapError, setMapError] = useState("");
  const mappedReports = reports.filter(report =>
    typeof report.latitude === "number" && typeof report.longitude === "number"
    && Number.isFinite(report.latitude) && Number.isFinite(report.longitude)
  );

  useEffect(() => {
    let map: any;
    let cancelled = false;
    loadLeaflet().then(() => {
      if (cancelled || !mapElement.current || !window.L) return;
      const L = window.L;
      map = L.map(mapElement.current).setView([30.0668, 79.0193], 7);
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
      window.setTimeout(() => map?.invalidateSize(), 100);
    }).catch(() => setMapError("मानचित्र लोड नहीं हो सका। इंटरनेट कनेक्शन जाँचें।"));
    return () => { cancelled = true; if (map) map.remove(); };
  }, [mappedReports.length, mappedReports.map(r => r.report_id + r.latitude + r.longitude).join("|")]);

  return <section className="command-section incident-map-section">
    <div className="section-heading"><div><p className="eyebrow">GPS-आधारित घटना स्थान</p><h3>उत्तराखंड घटना मानचित्र</h3></div><p>{mappedReports.length} स्थान मैप किए गए</p></div>
    <p className="map-disclaimer">केवल नागरिक द्वारा साझा किए गए GPS निर्देशांक दिखाए गए हैं। बिना GPS वाली रिपोर्ट मानचित्र पर नहीं दिखाई जातीं।</p>
    <div ref={mapElement} className="incident-map" role="application" aria-label="GPS incident map of Uttarakhand" />
    {mapError && <p className="dashboard-error">{mapError}</p>}
    {!mappedReports.length && <p className="map-empty">अभी किसी रिपोर्ट में GPS निर्देशांक नहीं हैं। अगली रिपोर्ट भेजते समय “मेरा GPS स्थान जोड़ें” दबाएँ। पुरानी रिपोर्टों के स्थान अपने-आप अनुमानित नहीं किए जाएँगे।</p>}
  </section>;
}
