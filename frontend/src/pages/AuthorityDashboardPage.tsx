import { useEffect, useState } from "react";
import { getReportIntelligence, getVillageImpacts, ReportIntelligence, VillageImpact } from "../api/client";

const categoryLabels: Record<string, string> = { landslide: "भूस्खलन", road_blockage: "सड़क अवरुद्ध", cloudburst: "बादल फटना", building_damage: "भवन क्षति", heavy_rainfall: "तेज़ बारिश", flood: "बाढ़", water_shortage: "पानी की कमी", electricity_disruption: "बिजली बाधित", medical_emergency: "चिकित्सा", other: "अन्य" };
const severityLabels: Record<string, string> = { LOW: "कम", MEDIUM: "मध्यम", HIGH: "उच्च", CRITICAL: "अत्यंत गंभीर" };

export function AuthorityDashboardPage() {
  const [impacts, setImpacts] = useState<VillageImpact[]>([]);
  const [reports, setReports] = useState<ReportIntelligence[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getVillageImpacts(), getReportIntelligence()])
      .then(([villageImpacts, reportIntelligence]) => { setImpacts(villageImpacts); setReports(reportIntelligence); })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return <section className="panel intelligence-panel">
    <p className="eyebrow">स्थानीय AI सहायता · अधिकारी दृश्य</p>
    <h2>गांव प्रभाव <span>इंटेलिजेंस</span></h2>
    <p className="intelligence-intro">AI से बने संकेत केवल सिफारिशें हैं, पुष्टि किए गए तथ्य नहीं। कार्रवाई से पहले हर प्राथमिकता और संभावित डुप्लिकेट का मानवीय सत्यापन आवश्यक है।</p>
    {loading && <p>डेटा लोड हो रहा है…</p>}
    {error && <p className="dashboard-error" role="alert">{error}</p>}
    {!loading && !error && <>
      <section aria-labelledby="village-intelligence-heading">
        <h3 className="dashboard-section-title" id="village-intelligence-heading">गांव-वार प्रभाव</h3>
        {impacts.length ? <div className="impact-grid">{impacts.map(impact => <article className="impact-card" key={impact.village_name}><div className="impact-heading"><div><p className="eyebrow">गांव</p><h3>{impact.village_name}</h3></div><strong>{impact.total_incidents}<small> रिपोर्ट</small></strong></div><div className="severity-row">{Object.entries(impact.severity_distribution).map(([severity, count]) => <span className={'severity severity-' + severity.toLowerCase()} key={severity}>{severityLabels[severity] ?? severity}: {count}</span>)}</div><p className="impact-label">घटना प्रकार</p><div className="distribution">{Object.entries(impact.category_distribution).map(([category, count]) => <span key={category}>{categoryLabels[category] ?? category} <b>{count}</b></span>)}</div>{impact.potentially_duplicated_reports > 0 && <p className="duplicate-note">⌁ {impact.potentially_duplicated_reports} रिपोर्ट संभावित रूप से समान — समीक्षा करें</p>}</article>)}</div> : <div className="empty-intelligence"><span>⛰</span><h3>अभी कोई रिपोर्ट नहीं</h3><p>नागरिक रिपोर्ट आने पर यहां गांव-वार प्रभाव और प्राथमिकता संकेत दिखेंगे।</p></div>}
      </section>

      <section className="incident-intelligence" aria-labelledby="incident-intelligence-heading">
        <div className="incident-section-heading"><div><p className="eyebrow">AI सिफारिश · मानवीय समीक्षा आवश्यक</p><h3 id="incident-intelligence-heading">घटना-स्तरीय इंटेलिजेंस</h3></div><span className="recommendation-badge">पुष्ट तथ्य नहीं</span></div>
        {reports.length ? <div className="incident-list">{reports.map(report => {
          const severity = report.severity.recommended_severity;
          const evidence = report.severity.evidence.length ? report.severity.evidence : report.classification.matched_keywords;
          return <article className="incident-card" key={report.report_id}>
            <div className="incident-card-heading"><div><p className="eyebrow">रिपोर्ट #{report.report_id}</p><h4>{report.village_name} <span>· {report.district}</span></h4></div><span className={'severity severity-' + severity.toLowerCase()}>{severityLabels[severity] ?? severity} प्राथमिकता</span></div>
            <dl className="incident-details">
              <div className="incident-description"><dt>मूल विवरण</dt><dd>{report.description}</dd></div>
              <div><dt>AI-वर्गीकृत श्रेणी <small>(सिफारिश)</small></dt><dd>{categoryLabels[report.classification.predicted_category] ?? report.classification.predicted_category}</dd></div>
              <div><dt>वर्गीकरण विश्वास</dt><dd>{Math.round(report.classification.confidence_score * 100)}%</dd></div>
              <div><dt>मिला हुआ प्रमाण</dt><dd>{evidence.length ? <span className="evidence-list">{evidence.map(item => <span key={item}>{item}</span>)}</span> : "कोई स्पष्ट शब्द-संकेत नहीं"}</dd></div>
              <div><dt>सुझाई गई गंभीरता <small>(AI सिफारिश)</small></dt><dd><span className={'severity severity-' + severity.toLowerCase()}>{severityLabels[severity] ?? severity}</span></dd></div>
              <div className="severity-explanation"><dt>गंभीरता का हिंदी कारण</dt><dd>{report.severity.explanation}</dd></div>
              <div><dt>मानवीय सत्यापन</dt><dd className={report.severity.human_verification_required ? "verification-required" : "verification-optional"}>{report.severity.human_verification_required ? "आवश्यक" : "अनुशंसित"}</dd></div>
            </dl>
            <div className="duplicate-review"><strong>संभावित डुप्लिकेट रिपोर्ट <small>(समीक्षा आवश्यक)</small></strong>{report.potential_duplicates.length ? <ul>{report.potential_duplicates.map(duplicate => <li key={duplicate.report_id}><b>#{duplicate.report_id}</b> — {duplicate.reason} <span>({Math.round(duplicate.similarity_score * 100)}% मिलान)</span></li>)}</ul> : <p>कोई संभावित डुप्लिकेट नहीं मिला।</p>}</div>
          </article>;
        })}</div> : <div className="empty-intelligence"><span>⌕</span><h3>अभी कोई घटना-स्तरीय रिपोर्ट नहीं</h3><p>नई नागरिक रिपोर्ट आने पर यहां AI सिफारिशें समीक्षा के लिए दिखेंगी।</p></div>}
      </section>
    </>}
  </section>;
}

