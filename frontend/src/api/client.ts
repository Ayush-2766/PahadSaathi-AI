export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
export async function getHealth(): Promise<{ status: string; database: string }> {
  const response = await fetch(apiBaseUrl + "/health");
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json();
}

export type ReportPayload = { category: string; villageName: string; district: string; description: string; photo?: File | null };
export async function submitCitizenReport(payload: ReportPayload): Promise<{ report_id: string; status: string }> {
  const body = new FormData();
  body.append("category", payload.category); body.append("village_name", payload.villageName); body.append("district", payload.district); body.append("description", payload.description);
  if (payload.photo) body.append("photo", payload.photo);
  const response = await fetch(apiBaseUrl + "/reports", { method: "POST", body }); const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail?.message ?? data.detail ?? "रिपोर्ट भेजा नहीं जा सका।");
  return data;
}

export type ReportStatus = "submitted" | "verified" | "in_progress" | "resolved" | "dismissed";
export async function updateReportStatus(reportId: string, status: ReportStatus): Promise<{ report_id: string; status: string }> {
  const response = await fetch(`${apiBaseUrl}/reports/${reportId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail?.message ?? data.detail ?? "स्थिति अपडेट नहीं की जा सकी।");
  return data;
}

export function getFullPhotoUrl(photoUrl: string | null | undefined): string {
  if (!photoUrl) return "";
  if (photoUrl.startsWith("http")) return photoUrl;
  const origin = apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  return `${origin}${photoUrl}`;
}

export type VillageImpact = { village_name: string; total_incidents: number; category_distribution: Record<string, number>; severity_distribution: Record<string, number>; potentially_duplicated_reports: number };
export async function getVillageImpacts(): Promise<VillageImpact[]> {
  const response = await fetch(apiBaseUrl + "/intelligence/villages");
  if (!response.ok) throw new Error("इंटेलिजेंस डेटा लोड नहीं हो सका।");
  return response.json();
}

export type IncidentClassification = { predicted_category: string; confidence_score: number; matched_keywords: string[] };
export type SeverityRecommendation = { recommended_severity: string; explanation: string; evidence: string[]; human_verification_required: boolean };
export type PotentialDuplicate = { report_id: string; similarity_score: number; reason: string };
export type ReportIntelligence = {
  report_id: string;
  village_name: string;
  district: string;
  description: string;
  status: string;
  submitted_at: string;
  photo_url?: string | null;
  classification: IncidentClassification;
  severity: SeverityRecommendation;
  potential_duplicates: PotentialDuplicate[];
};
export async function getReportIntelligence(): Promise<ReportIntelligence[]> {
  const response = await fetch(apiBaseUrl + "/intelligence/reports");
  if (!response.ok) throw new Error("घटना इंटेलिजेंस डेटा लोड नहीं हो सका।");
  return response.json();
}
export async function getReportIntelligenceById(reportId: string): Promise<ReportIntelligence | undefined> {
  return (await getReportIntelligence()).find((report) => report.report_id === reportId);
}

export type IncidentBriefReport = {
  report_id: string;
  village_name: string;
  district: string;
  description: string;
  submitted_at: string;
  reported_category: string;
  ai_category: string;
  status?: string;
  photo_url?: string | null;
};
export type AuthorityAction = { priority: number; action: string; basis: string };
export type IncidentBrief = {
  incident_id: string;
  situation_summary: string;
  contributing_reports: IncidentBriefReport[];
  affected_villages: string[];
  highest_recommended_severity: string;
  detected_facts: string[];
  inferred_relationships: string[];
  recommended_verification_steps: string[];
  prioritized_authority_actions: AuthorityAction[];
};
export async function getIncidentBriefs(): Promise<IncidentBrief[]> {
  const response = await fetch(apiBaseUrl + "/intelligence/incidents");
  if (!response.ok) throw new Error("आपातकालीन इंटेलिजेंस डेटा लोड नहीं हो सका।");
  return response.json();
}

