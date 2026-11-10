export const DRAFT_STORAGE_KEY = "pahadsaathi.citizen-report-draft";
export function saveDraft(storage, draft) { storage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft)); }
export function loadDraft(storage) { const saved = storage.getItem(DRAFT_STORAGE_KEY); if (!saved) return null; try { return JSON.parse(saved); } catch { storage.removeItem(DRAFT_STORAGE_KEY); return null; } }
export function clearDraft(storage) { storage.removeItem(DRAFT_STORAGE_KEY); }
