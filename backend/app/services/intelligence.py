"""Explainable, local rules for incident triage. These are recommendations only."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from app.models.citizen_report import CitizenReport

CATEGORY_KEYWORDS = {
    "landslide": ("landslide", "भूस्खलन", "मलबा", "पहाड़ी गिरी", "चट्टान", "pahad gir gaya", "pahad gira", "malba gira", "malba aa gaya", "पहाड़ गिर गया", "मलबा गिरा"),
    "road_blockage": ("road blockage", "road blocked", "road block", "road band", "sadak band", "सड़क बंद", "सड़क अवरुद्ध", "रास्ता बंद", "आवाजाही बंद"),
    "cloudburst": ("cloudburst", "badal phata", "बादल फटा"),
    "building_damage": ("building damage", "house collapsed", "ghar toot gaya", "घर टूट गया", "मकान टूट गया", "घर ढह गया"),
    "heavy_rainfall": ("heavy rainfall", "heavy rain", "तेज बारिश", "भारी बारिश", "लगातार बारिश"),
    "flood": ("flood", "बाढ़", "जलभराव", "नदी उफान", "पानी भर"),
    "water_shortage": ("water shortage", "water not coming", "pani nahi aa raha", "paani nahi aa raha", "पानी की कमी", "पेयजल", "पानी नहीं", "पानी नहीं आ रहा"),
    "electricity_disruption": ("electricity", "power cut", "bijli nahi hai", "bijli nahi aa rahi", "बिजली", "विद्युत", "लाइट नहीं", "बिजली नहीं है"),
    "medical_emergency": ("medical emergency", "injured", "injury", "medical", "घायल", "चिकित्सा", "अस्पताल", "मरीज"),
}
HIGH_RISK_WORDS = ("trapped", "injured", "injury", "dead", "collapsed", "evacuate", "फंसे", "घायल", "मौत", "गिर गया", "निकालें")
CRITICAL_RISK_WORDS = ("life threatening", "many injured", "people trapped", "बचाओ", "जान का खतरा", "कई घायल", "लोग फंसे")


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def classify_incident(description: str, reported_category: str | None = None) -> dict:
    text = _normalise(description)
    matches = {category: [word for word in words if word in text] for category, words in CATEGORY_KEYWORDS.items()}
    matches = {category: words for category, words in matches.items() if words}
    if matches:
        # Dictionary order is the explicit domain priority when the same number
        # of keywords supports two categories, keeping the result predictable.
        predicted, evidence = max(matches.items(), key=lambda item: len(item[1]))
        confidence = min(0.95, 0.55 + 0.15 * len(evidence))
        return {"predicted_category": predicted, "confidence_score": round(confidence, 2), "matched_keywords": evidence}
    if reported_category and reported_category != "other":
        return {"predicted_category": reported_category, "confidence_score": 0.4, "matched_keywords": ["reported category"]}
    return {"predicted_category": "other", "confidence_score": 0.2, "matched_keywords": []}


def recommend_severity(category: str, description: str, classification_evidence: list[str]) -> dict:
    text = _normalise(description)
    critical = [word for word in CRITICAL_RISK_WORDS if word in text]
    high_risk = [word for word in HIGH_RISK_WORDS if word in text]
    evidence = list(classification_evidence) + critical + high_risk
    if critical or (category == "medical_emergency" and high_risk):
        level = "CRITICAL"
    elif high_risk or category in {"landslide", "flood", "medical_emergency"}:
        level = "HIGH"
    elif category in {"road_blockage", "heavy_rainfall", "electricity_disruption", "water_shortage"}:
        level = "MEDIUM"
    else:
        level = "LOW"
    explanation = f"यह उपलब्ध शब्दों और घटना के प्रकार पर आधारित {level} प्राथमिकता की सिफारिश है; अधिकारी द्वारा सत्यापन आवश्यक है।"
    return {"recommended_severity": level, "explanation": explanation, "evidence": list(dict.fromkeys(evidence)), "human_verification_required": True}


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w\u0900-\u097F]+", _normalise(value)))


def _description_similarity(first: str, second: str) -> float:
    first_tokens, second_tokens = _tokens(first), _tokens(second)
    token_score = len(first_tokens & second_tokens) / len(first_tokens | second_tokens) if first_tokens | second_tokens else 0
    character_score = SequenceMatcher(None, _normalise(first), _normalise(second)).ratio()
    return round(max(token_score, character_score), 2)


def find_potential_duplicates(incoming: dict, reports: list[CitizenReport], category: str) -> list[dict]:
    submitted_at = incoming.get("submitted_at") or datetime.utcnow()
    village = _normalise(incoming.get("village_name") or "")
    matches = []
    for report in reports:
        # Analysing a persisted report must never return that same row as a
        # duplicate.  public_id is stable across API and database boundaries.
        if incoming.get("report_id") and report.public_id == incoming["report_id"]:
            continue
        if village and _normalise(report.village_name) != village:
            continue
        existing_category = classify_incident(report.description, report.category)["predicted_category"]
        similarity = _description_similarity(incoming["description"], report.description)
        time_close = abs(submitted_at - report.submitted_at) <= timedelta(hours=48)
        category_match = category == existing_category
        # Location/category alone are common in a village during an emergency.
        # Always require a substantial description signal; a higher threshold
        # for cross-category reports prevents incidental wording matches.
        meaningful_similarity = similarity >= (0.48 if category_match else 0.72)
        if meaningful_similarity and (category_match or time_close):
            reasons = ["same village"]
            if category_match:
                reasons.append("same incident category")
            if time_close:
                reasons.append("reported within 48 hours")
            reasons.append(f"description similarity {similarity:.0%}")
            matches.append({"report_id": report.public_id, "similarity_score": similarity, "reason": "; ".join(reasons)})
    return sorted(matches, key=lambda item: item["similarity_score"], reverse=True)


def village_impacts(reports: list[CitizenReport]) -> list[dict]:
    grouped: dict[str, list[CitizenReport]] = defaultdict(list)
    for report in reports:
        grouped[report.village_name].append(report)
    output = []
    for village, village_reports in grouped.items():
        categories, severities = Counter(), Counter()
        duplicate_ids = set()
        for report in village_reports:
            classification = classify_incident(report.description, report.category)
            categories[classification["predicted_category"]] += 1
            severity = recommend_severity(classification["predicted_category"], report.description, classification["matched_keywords"])
            severities[severity["recommended_severity"]] += 1
            others = [candidate for candidate in village_reports if candidate.public_id != report.public_id]
            for duplicate in find_potential_duplicates({"description": report.description, "village_name": report.village_name, "submitted_at": report.submitted_at}, others, classification["predicted_category"]):
                duplicate_ids.update((report.public_id, duplicate["report_id"]))
        output.append({"village_name": village, "total_incidents": len(village_reports), "category_distribution": dict(categories), "severity_distribution": dict(severities), "potentially_duplicated_reports": len(duplicate_ids)})
    return sorted(output, key=lambda item: (-item["total_incidents"], item["village_name"]))
