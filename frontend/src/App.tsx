import { useState } from "react";
import { AuthorityDashboardPage } from "./pages/AuthorityDashboardPage";
import { CitizenReportPage } from "./pages/CitizenReportPage";
import "./styles/global.css";
type Page = "report" | "dashboard";
export default function App() {
  const [page, setPage] = useState<Page>("report");
  return <main className="app-shell"><header className="site-header"><div className="brand"><span className="brand-mark" aria-hidden="true">⛰</span><div><p className="eyebrow">उत्तराखंड आपदा सहायता</p><h1>PahadSaathi <span>AI</span></h1></div></div><nav aria-label="मुख्य नेविगेशन"><button className={page === "report" ? "active" : ""} onClick={() => setPage("report")}>रिपोर्ट भेजें</button><button className={page === "dashboard" ? "active" : ""} onClick={() => setPage("dashboard")}>अधिकारी डैशबोर्ड</button></nav></header>{page === "report" ? <CitizenReportPage /> : <AuthorityDashboardPage />}</main>;
}

