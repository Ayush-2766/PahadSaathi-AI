import { useEffect, useMemo, useState } from "react";
import {
  getFullPhotoUrl,
  getHealth,
  getIncidentBriefs,
  getReportIntelligence,
  getVillageImpacts,
  IncidentBrief,
  ReportIntelligence,
  ReportStatus,
  updateReportStatus,
  VillageImpact,
} from "../api/client";

const categoryLabels: Record<string, string> = {
  landslide: "भूस्खलन",
  road_blockage: "सड़क अवरुद्ध",
  cloudburst: "बादल फटना",
  building_damage: "भवन क्षति",
  heavy_rainfall: "तेज़ बारिश",
  flood: "बाढ़",
  water_shortage: "पानी की कमी",
  electricity_disruption: "बिजली बाधित",
  medical_emergency: "चिकित्सा",
  other: "अन्य",
};
const severityLabels: Record<string, string> = { LOW: "कम", MEDIUM: "मध्यम", HIGH: "उच्च", CRITICAL: "अत्यंत गंभीर" };
const statusLabels: Record<string, string> = {
  submitted: "दर्ज (लंबित)",
  verified: "सत्यापित",
  in_progress: "कार्रवाई जारी",
  resolved: "समाधान संपन्न",
  dismissed: "खारिज",
};

export function formatIST(dateString: string | Date | undefined): string {
  if (!dateString) return "";
  let str = typeof dateString === "string" ? dateString.trim() : dateString.toISOString();
  if (!str.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(str)) {
    str = str.replace(" ", "T") + "Z";
  }
  const date = new Date(str);
  if (isNaN(date.getTime())) return String(dateString);
  return new Intl.DateTimeFormat("hi-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date) + " IST";
}

function SeverityBadge({ severity }: { severity: string }) {
  return <span className={'severity severity-' + severity.toLowerCase()}>{severityLabels[severity] ?? severity}</span>;
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status}`}>{statusLabels[status] ?? status}</span>;
}

export function AuthorityDashboardPage() {
  const [impacts, setImpacts] = useState<VillageImpact[]>([]);
  const [reports, setReports] = useState<ReportIntelligence[]>([]);
  const [briefs, setBriefs] = useState<IncidentBrief[]>([]);
  const [health, setHealth] = useState<{ status: string; database: string } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [statusStates, setStatusStates] = useState<Record<string, { loading?: boolean; success?: string; error?: string }>>({});

  useEffect(() => {
    Promise.all([getVillageImpacts(), getReportIntelligence(), getIncidentBriefs()])
      .then(([villageImpacts, reportIntelligence, incidentBriefs]) => {
        setImpacts(villageImpacts);
        setReports(reportIntelligence);
        setBriefs(incidentBriefs);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  async function handleStatusChange(reportId: string, nextStatus: ReportStatus) {
    setStatusStates(prev => ({ ...prev, [reportId]: { loading: true } }));
    try {
      await updateReportStatus(reportId, nextStatus);
      setReports(prev => prev.map(r => r.report_id === reportId ? { ...r, status: nextStatus } : r));
      setStatusStates(prev => ({
        ...prev,
        [reportId]: { success: `स्थिति '${statusLabels[nextStatus] ?? nextStatus}' अपडेट हो गई।` },
      }));
      setTimeout(() => {
        setStatusStates(prev => {
          const copy = { ...prev };
          if (copy[reportId]?.success) delete copy[reportId];
          return copy;
        });
      }, 3500);
    } catch (err) {
      setStatusStates(prev => ({
        ...prev,
        [reportId]: { error: err instanceof Error ? err.message : "स्थिति अपडेट करने में त्रुटि।" },
      }));
    }
  }

  const summary = useMemo(() => ({
    highPriority: reports.filter(report => ["HIGH", "CRITICAL"].includes(report.severity.recommended_severity)).length,
    duplicateReports: reports.filter(report => report.potential_duplicates.length > 0).length,
    highestVillageCount: Math.max(...impacts.map(impact => impact.total_incidents), 1),
  }), [impacts, reports]);

  return (
    <section className="command-centre">
      <header className="command-hero">
        <div className="command-kicker">
          <span className="command-mark" aria-hidden="true">⌁</span> उत्तराखंड आपदा प्रबंधन
        </div>
        <div className="command-hero-content">
          <div>
            <h2>PahadSaathi <em>स्थिति केंद्र</em></h2>
            <p>उत्तराखंड घटना प्रतिक्रिया केंद्र</p>
          </div>
          {health && (
            <div className="system-status" title={`API: ${health.status}; Database: ${health.database}`}>
              <span aria-hidden="true"></span>
              <div>
                <small>सिस्टम स्थिति</small>
                <strong>{health.status} · {health.database}</strong>
              </div>
            </div>
          )}
        </div>
        <p className="command-disclaimer">
          नियम-आधारित विश्लेषण कार्रवाई के लिए सिफारिश है, पुष्टि किया गया तथ्य नहीं। हर घटना का मानवीय सत्यापन आवश्यक है।
        </p>
      </header>

      {loading && <section className="command-loading" aria-live="polite">कमान केंद्र डेटा लोड हो रहा है…</section>}
      {error && <p className="dashboard-error command-error" role="alert">{error}</p>}

      {!loading && !error && (
        <>
          <section className="operational-summary" aria-labelledby="summary-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">वर्तमान स्थिति</p>
                <h3 id="summary-heading">परिचालन सारांश</h3>
              </div>
              <p>रिपोर्ट किए गए डेटा पर आधारित</p>
            </div>
            <div className="summary-grid">
              <article>
                <span className="summary-icon forest">▣</span>
                <div>
                  <strong>{reports.length}</strong>
                  <p>कुल रिपोर्ट की गई घटनाएं</p>
                </div>
              </article>
              <article>
                <span className="summary-icon alert">!</span>
                <div>
                  <strong>{summary.highPriority}</strong>
                  <p>उच्च / अत्यंत गंभीर सिफारिशें</p>
                </div>
              </article>
              <article>
                <span className="summary-icon earth">⌂</span>
                <div>
                  <strong>{impacts.length}</strong>
                  <p>प्रभावित गांव</p>
                </div>
              </article>
              <article>
                <span className="summary-icon amber">⌁</span>
                <div>
                  <strong>{summary.duplicateReports}</strong>
                  <p>संभावित डुप्लिकेट रिपोर्ट</p>
                </div>
              </article>
            </div>
          </section>

          <section className="command-section emergency-intelligence" aria-labelledby="emergency-intelligence-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">घटना फ्यूज़न · मानवीय समीक्षा आवश्यक</p>
                <h3 id="emergency-intelligence-heading">आपातकालीन इंटेलिजेंस ब्रीफ</h3>
              </div>
              <span className="recommendation-badge">संभावित, पुष्ट नहीं</span>
            </div>
            <p className="emergency-intro">
              यह पैनल केवल मज़बूत स्थान, समय, श्रेणी और विवरण संकेतों वाले रिपोर्ट-समूह दिखाता है। तथ्य, अनुमान और कार्रवाई-सिफारिशें अलग रखी गई हैं।
            </p>
            {briefs.length ? (
              <div className="brief-list">
                {briefs.map(brief => (
                  <EmergencyBriefCard key={brief.incident_id} brief={brief} />
                ))}
              </div>
            ) : (
              <EmptyState title="कोई संभावित संयुक्त घटना नहीं मिली" message="असंबंधित रिपोर्ट को जोड़ने से बचने के लिए केवल पर्याप्त संकेत वाले समूह यहां दिखेंगे।" />
            )}
          </section>

          <section className="command-section intelligence-command" aria-labelledby="incident-intelligence-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">नियम-आधारित सिफारिश · समीक्षा एवं कार्रवाई</p>
                <h3 id="incident-intelligence-heading">व्यक्तिगत रिपोर्ट इंटेलिजेंस</h3>
              </div>
              <span className="recommendation-badge">पुष्ट तथ्य नहीं</span>
            </div>
            {reports.length ? (
              <div className="incident-list">
                {reports.map(report => (
                  <IncidentCard
                    key={report.report_id}
                    report={report}
                    onStatusChange={handleStatusChange}
                    statusState={statusStates[report.report_id]}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="अभी कोई घटना-स्तरीय रिपोर्ट नहीं" message="नई नागरिक रिपोर्ट आने पर यहां नियम-आधारित सिफारिशें समीक्षा के लिए दिखेंगी।" />
            )}
          </section>

          <section className="command-section geographic-overview" aria-labelledby="geographic-overview-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">स्थान-आधारित सारांश</p>
                <h3 id="geographic-overview-heading">गांव-वार प्रभाव</h3>
              </div>
              <p>मानचित्र निर्देशांक उपलब्ध नहीं हैं</p>
            </div>
            {impacts.length ? (
              <div className="village-overview">
                {impacts.map(impact => (
                  <article className="village-row" key={impact.village_name}>
                    <div className="village-row-head">
                      <div>
                        <h4>{impact.village_name}</h4>
                        <p>{impact.total_incidents} रिपोर्ट · {impact.potentially_duplicated_reports} संभावित डुप्लिकेट</p>
                      </div>
                      <strong>{impact.total_incidents}</strong>
                    </div>
                    <div className="village-bar" aria-label={`${impact.village_name}: ${impact.total_incidents} reports`}>
                      <span style={{ width: `${(impact.total_incidents / summary.highestVillageCount) * 100}%` }}></span>
                    </div>
                    <div className="village-signals">
                      {Object.entries(impact.severity_distribution).map(([severity, count]) => (
                        <span key={severity}><SeverityBadge severity={severity} /> {count}</span>
                      ))}
                      {Object.entries(impact.category_distribution).map(([category, count]) => (
                        <span className="category-signal" key={category}>{categoryLabels[category] ?? category} <b>{count}</b></span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState title="अभी कोई गांव-स्तरीय डेटा नहीं" message="रिपोर्ट आने पर गांव-वार घटना वितरण यहां दिखेगा।" />
            )}
          </section>
        </>
      )}
    </section>
  );
}

function IncidentCard({
  report,
  onStatusChange,
  statusState,
}: {
  report: ReportIntelligence;
  onStatusChange: (reportId: string, nextStatus: ReportStatus) => void;
  statusState?: { loading?: boolean; success?: string; error?: string };
}) {
  const severity = report.severity.recommended_severity;
  const evidence = report.severity.evidence.length ? report.severity.evidence : report.classification.matched_keywords;
  const currentStatus = report.status ?? "submitted";

  return (
    <article className="incident-card command-incident-card">
      <div className="incident-card-heading">
        <div>
          <div className="incident-meta-row">
            <p className="eyebrow">रिपोर्ट #{report.report_id}</p>
            {report.submitted_at && (
              <span className="incident-timestamp" title="भारतीय मानक समय (IST)">
                🕒 {formatIST(report.submitted_at)}
              </span>
            )}
          </div>
          <h4>{report.village_name} <span>· {report.district}</span></h4>
        </div>
        <div className="severity-command">
          <small>सुझाई गई गंभीरता</small>
          <SeverityBadge severity={severity} />
        </div>
      </div>

      <p className="incident-narrative">{report.description}</p>

      {report.photo_url && (
        <div className="report-photo-container">
          <span className="control-label">संलग्न फोटोग्राफ:</span>
          <a
            href={getFullPhotoUrl(report.photo_url)}
            target="_blank"
            rel="noopener noreferrer"
            className="photo-preview-link"
            title="बड़ा चित्र देखने के लिए क्लिक करें"
          >
            <img
              src={getFullPhotoUrl(report.photo_url)}
              alt={`रिपोर्ट #${report.report_id} संलग्न फोटो`}
              className="report-photo-thumb"
              loading="lazy"
            />
            <span className="photo-zoom-hint">चित्र बड़ा देखने के लिए क्लिक करें ↗</span>
          </a>
        </div>
      )}

      <dl className="incident-details command-details">
        <div>
          <dt>AI-वर्गीकृत श्रेणी <small>सिफारिश</small></dt>
          <dd>{categoryLabels[report.classification.predicted_category] ?? report.classification.predicted_category}</dd>
        </div>
        <div>
          <dt>वर्गीकरण विश्वास</dt>
          <dd className="confidence-value">{Math.round(report.classification.confidence_score * 100)}%</dd>
        </div>
        <div className="incident-evidence">
          <dt>मिला हुआ प्रमाण</dt>
          <dd>
            {evidence.length ? (
              <span className="evidence-list">
                {evidence.map(item => <span key={item}>{item}</span>)}
              </span>
            ) : "कोई स्पष्ट शब्द-संकेत नहीं"}
          </dd>
        </div>
        <div>
          <dt>मानवीय सत्यापन</dt>
          <dd className={report.severity.human_verification_required ? "verification-required" : "verification-optional"}>
            {report.severity.human_verification_required ? "आवश्यक" : "अनुशंसित"}
          </dd>
        </div>
        <div className="severity-explanation">
          <dt>AI गंभीरता कारण</dt>
          <dd>{report.severity.explanation}</dd>
        </div>
      </dl>

      <div className="status-transition-panel">
        <div className="status-transition-header">
          <div className="status-current">
            <span className="control-label">वर्तमान स्थिति:</span>
            <StatusBadge status={currentStatus} />
          </div>
        </div>
        <div className="status-actions">
          <label htmlFor={`status-select-${report.report_id}`} className="control-label">स्थिति बदलें:</label>
          <select
            id={`status-select-${report.report_id}`}
            className="status-select"
            value={currentStatus}
            disabled={statusState?.loading}
            onChange={(e) => onStatusChange(report.report_id, e.target.value as ReportStatus)}
            aria-label={`रिपोर्ट #${report.report_id} की स्थिति बदलें`}
          >
            <option value="submitted">दर्ज (लंबित / Submitted)</option>
            <option value="verified">सत्यापित (Verified)</option>
            <option value="in_progress">कार्रवाई जारी (In Progress)</option>
            <option value="resolved">समाधान संपन्न (Resolved)</option>
            <option value="dismissed">खारिज (Dismissed)</option>
          </select>
          {currentStatus === "submitted" && (
            <button
              type="button"
              className="status-btn btn-verify"
              disabled={statusState?.loading}
              onClick={() => onStatusChange(report.report_id, "verified")}
            >
              ✓ सत्यापित करें
            </button>
          )}
          {currentStatus === "verified" && (
            <button
              type="button"
              className="status-btn btn-progress"
              disabled={statusState?.loading}
              onClick={() => onStatusChange(report.report_id, "in_progress")}
            >
              ▶ कार्रवाई शुरू
            </button>
          )}
          {currentStatus === "in_progress" && (
            <button
              type="button"
              className="status-btn btn-resolve"
              disabled={statusState?.loading}
              onClick={() => onStatusChange(report.report_id, "resolved")}
            >
              ✓ समाधान संपन्न
            </button>
          )}
        </div>
        {statusState?.loading && <p className="status-feedback loading" role="status">स्थिति अपडेट हो रही है…</p>}
        {statusState?.success && <p className="status-feedback success" role="status">✓ {statusState.success}</p>}
        {statusState?.error && <p className="status-feedback error" role="alert">! {statusState.error}</p>}
      </div>

      <div className="duplicate-review">
        <strong>संभावित डुप्लिकेट <small>समीक्षा आवश्यक</small></strong>
        {report.potential_duplicates.length ? (
          <ul>
            {report.potential_duplicates.map(duplicate => (
              <li key={duplicate.report_id}>
                <b>#{duplicate.report_id}</b> — {duplicate.reason} <span>({Math.round(duplicate.similarity_score * 100)}% मिलान)</span>
              </li>
            ))}
          </ul>
        ) : (
          <p>कोई संभावित डुप्लिकेट नहीं मिला।</p>
        )}
      </div>
    </article>
  );
}

function EmergencyBriefCard({ brief }: { brief: IncidentBrief }) {
  return (
    <article className="emergency-brief">
      <div className="incident-card-heading">
        <div>
          <p className="eyebrow">संभावित घटना · {brief.incident_id}</p>
          <h4>{brief.affected_villages.join(", ")}</h4>
        </div>
        <div className="severity-command">
          <small>उच्चतम सुझाई गंभीरता</small>
          <SeverityBadge severity={brief.highest_recommended_severity} />
        </div>
      </div>
      <p className="brief-summary">{brief.situation_summary}</p>
      <div className="brief-grid">
        <BriefSection title="रिपोर्ट किए गए तथ्य" items={brief.detected_facts} />
        <BriefSection title="अनुमानित संबंध" items={brief.inferred_relationships} />
        <BriefSection title="सत्यापन के अगले कदम" items={brief.recommended_verification_steps} />
        <div className="brief-section">
          <h5>प्राथमिकता कार्रवाई-सिफारिशें</h5>
          <ol>
            {brief.prioritized_authority_actions.map(item => (
              <li key={item.priority}>
                <strong>{item.action}</strong>
                <span>{item.basis}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
      <div className="contributing-reports">
        <strong>योगदान देने वाली रिपोर्ट ({brief.contributing_reports.length})</strong>
        {brief.contributing_reports.map(report => (
          <div key={report.report_id} className="contributing-report-item">
            <div className="contributing-report-head">
              <b>#{report.report_id}</b> · {report.village_name}
              {report.status && <StatusBadge status={report.status} />}
              {report.submitted_at && <span className="contributing-time">· {formatIST(report.submitted_at)}</span>}
            </div>
            <p>{report.description}</p>
            {report.photo_url && (
              <a href={getFullPhotoUrl(report.photo_url)} target="_blank" rel="noopener noreferrer">
                <img src={getFullPhotoUrl(report.photo_url)} alt="संलग्न फोटो" className="contributing-thumb" loading="lazy" />
              </a>
            )}
          </div>
        ))}
      </div>
    </article>
  );
}

function BriefSection({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="brief-section">
      <h5>{title}</h5>
      <ul>
        {items.map(item => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="empty-intelligence command-empty">
      <span>⛰</span>
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}
