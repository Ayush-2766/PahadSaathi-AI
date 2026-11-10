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
  classification: IncidentClassification;
  severity: SeverityRecommendation;
  potential_duplicates: PotentialDuplicate[];
};
export async function getReportIntelligence(): Promise<ReportIntelligence[]> {
  const response = await fetch(apiBaseUrl + "/intelligence/reports");
  if (!response.ok) throw new Error("घटना इंटेलिजेंस डेटा लोड नहीं हो सका।");
  return response.json();
}

