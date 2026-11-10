import assert from "node:assert/strict";
import test from "node:test";
import { DRAFT_STORAGE_KEY, clearDraft, loadDraft, saveDraft } from "../src/lib/reportDrafts.js";
function storage() { const values = new Map(); return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }; }
test("offline report drafts are saved and recovered", () => { const localStorage = storage(); const draft = { category: "flood", villageName: "जोशीमठ", district: "चमोली", description: "नदी का पानी बढ़ रहा है" }; saveDraft(localStorage, draft); assert.equal(localStorage.getItem(DRAFT_STORAGE_KEY), JSON.stringify(draft)); assert.deepEqual(loadDraft(localStorage), draft); clearDraft(localStorage); assert.equal(loadDraft(localStorage), null); });
