export interface ReportDraft {
  [key: string]: unknown;
}

export const DRAFT_STORAGE_KEY: string;

export function saveDraft(
  storage: Storage,
  draft: ReportDraft
): void;

export function loadDraft(
  storage: Storage
): ReportDraft | null;

export function clearDraft(storage: Storage): void;