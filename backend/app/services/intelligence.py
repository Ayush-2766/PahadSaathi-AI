"""Explainable, local rules for incident triage. These are recommendations only."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from app.models.citizen_report import CitizenReport

CATEGORY_KEYWORDS = {
    "landslide": ("landslide", "भूस्खलन", "मलबा", "पहाड़ी गिरी", "चट्टान", "pahad gir gaya", "pahad gira", "malba gira", "malba aa gaya", "पहाड़ गिर गया", "मलबा गिरा"),
    "road_blockage": (
        "road blockage", "road blocked", "road block", "road band",
        "sadak band", "सड़क बंद", "सड़क अवरुद्ध", "रास्ता बंद",
        "आवाजाही बंद", "rod block", "rod blocked",
        "rod block ho gyi", "road block ho gyi",
        "road band ho gaya", "raasta band", "rasta band",
        "sadak band ho gayi", "malba se road band",
    ),
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


ROMANIZED_VARIANTS = (
    (re.compile(r"\b(?:rod|road)\s+block(?:age|ed)?\b"), "road blockage"),
    (re.compile(r"\bsadak\s+band\b"), "road blockage"),
)


def _normalise(value: str) -> str:
    normalised = re.sub(r"\s+", " ", value.lower()).strip()
    for pattern, replacement in ROMANIZED_VARIANTS:
        normalised = pattern.sub(replacement, normalised)
    return normalised


def normalise_place_name(value: str) -> str:
    """Create a stable display/key form without changing the source report."""
    collapsed = re.sub(r"\s+", " ", value).strip()
    # Title case only Latin place names; Hindi has no casing and is preserved.
    if re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", collapsed):
        return collapsed.title()
    return collapsed


def place_key(value: str) -> str:
    """Comparison key for spelling/case/spacing variants of a reported place."""
    return _normalise(normalise_place_name(value)).casefold()


CATEGORY_PRIORITY = {
    "medical_emergency": 100,
    "cloudburst": 90,
    "landslide": 80,
    "flood": 70,
    "building_damage": 60,
    "road_blockage": 50,
    "heavy_rainfall": 40,
    "electricity_disruption": 30,
    "water_shortage": 20,
    "other": 10,
}


def classify_incident(description: str, reported_category: str | None = None) -> dict:
    text = _normalise(description)
    matches = {category: [word for word in words if word in text] for category, words in CATEGORY_KEYWORDS.items()}
    matches = {category: words for category, words in matches.items() if words}
    if matches:
        # Domain priority breaks ties when the same number of keywords
        # supports multiple categories, prioritizing life-safety without
        # overriding stronger evidence from another category.
        predicted, evidence = max(
            matches.items(),
            key=lambda item: (len(item[1]), CATEGORY_PRIORITY.get(item[0], 0)),
        )
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
    if category == "cloudburst" or critical:
        level = "CRITICAL"
    elif high_risk or category in {"landslide", "flood", "medical_emergency", "building_damage"}:
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


def _incident_keyword_overlap(first: str, second: str, category: str) -> tuple[float, list[str]]:
    """Return shared category evidence after spelling/transliteration normalisation."""
    keywords = {_normalise(keyword) for keyword in CATEGORY_KEYWORDS.get(category, ())}
    first_text, second_text = _normalise(first), _normalise(second)
    first_matches = {keyword for keyword in keywords if keyword in first_text}
    second_matches = {keyword for keyword in keywords if keyword in second_text}
    shared = sorted(first_matches & second_matches)
    all_matches = first_matches | second_matches
    score = len(shared) / len(all_matches) if all_matches else 0.0
    return score, shared


def find_potential_duplicates(incoming: dict, reports: list[CitizenReport], category: str) -> list[dict]:
    submitted_at = incoming.get("submitted_at") or datetime.utcnow()
    village = place_key(incoming.get("village_name") or "")
    matches = []
    for report in reports:
        # Analysing a persisted report must never return that same row as a
        # duplicate.  public_id is stable across API and database boundaries.
        if incoming.get("report_id") and report.public_id == incoming["report_id"]:
            continue
        if village and place_key(report.village_name) != village:
            continue
        existing_category = classify_incident(report.description, report.category)["predicted_category"]
        description_similarity = _description_similarity(incoming["description"], report.description)
        time_close = abs(submitted_at - report.submitted_at) <= timedelta(hours=48)
        category_match = category == existing_category
        keyword_overlap, shared_keywords = _incident_keyword_overlap(incoming["description"], report.description, category) if category_match else (0.0, [])
        similarity = round((description_similarity * 0.65) + (keyword_overlap * 0.35), 2)
        # Location/category alone are common in a village during an emergency.
        # Shared category evidence can help with spelling variants, but it may
        # not independently create a match: descriptions still need a signal.
        meaningful_similarity = (
            description_similarity >= 0.48
            or (category_match and keyword_overlap > 0 and description_similarity >= 0.30)
        ) if category_match else description_similarity >= 0.72
        if meaningful_similarity and time_close:
            reasons = ["same village"]
            if category_match:
                reasons.append("same incident category")
            if shared_keywords:
                reasons.append("shared incident keywords: " + ", ".join(shared_keywords))
            if time_close:
                reasons.append("reported within 48 hours")
            reasons.append(f"description similarity {description_similarity:.0%}")
            matches.append({"report_id": report.public_id, "similarity_score": similarity, "reason": "; ".join(reasons)})
    return sorted(matches, key=lambda item: item["similarity_score"], reverse=True)


def village_impacts(reports: list[CitizenReport]) -> list[dict]:
    grouped: dict[str, list[CitizenReport]] = defaultdict(list)
    village_names: dict[str, str] = {}

    for report in reports:
        display_name = normalise_place_name(report.village_name)
        village_key = place_key(display_name)

        grouped[village_key].append(report)

        # Prefer a properly capitalised display name.
        existing_name = village_names.get(village_key)
        if not existing_name or (
            existing_name == existing_name.lower()
            and display_name != display_name.lower()
        ):
            village_names[village_key] = display_name

    output = []

    for village_key, village_reports in grouped.items():
        categories, severities = Counter(), Counter()
        duplicate_ids = set()

        for report in village_reports:
            classification = classify_incident(
                report.description, report.category
            )
            categories[classification["predicted_category"]] += 1

            severity = recommend_severity(
                classification["predicted_category"],
                report.description,
                classification["matched_keywords"],
            )
            severities[severity["recommended_severity"]] += 1

            others = [
                candidate for candidate in village_reports
                if candidate.public_id != report.public_id
            ]

            for duplicate in find_potential_duplicates(
                {
                    "description": report.description,
                    "village_name": report.village_name,
                    "submitted_at": report.submitted_at,
                },
                others,
                classification["predicted_category"],
            ):
                duplicate_ids.update(
                    (report.public_id, duplicate["report_id"])
                )

        output.append({
            "village_name": village_names[village_key],
            "total_incidents": len(village_reports),
            "category_distribution": dict(categories),
            "severity_distribution": dict(severities),
            "potentially_duplicated_reports": len(duplicate_ids),
        })

    return sorted(
        output,
        key=lambda item: (-item["total_incidents"], item["village_name"]),
    )


SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _report_analysis(report: CitizenReport) -> dict:
    classification = classify_incident(report.description, report.category)
    severity = recommend_severity(
        classification["predicted_category"], report.description,
        classification["matched_keywords"],
    )
    return {"classification": classification, "severity": severity}


def _relationship(first: CitizenReport, second: CitizenReport, first_analysis: dict, second_analysis: dict) -> dict | None:
    """Return a deliberately conservative, explainable possible relationship."""
    category = first_analysis["classification"]["predicted_category"]
    if category != second_analysis["classification"]["predicted_category"]:
        return None
    time_difference = abs(first.submitted_at - second.submitted_at)
    if time_difference > timedelta(hours=48):
        return None

    same_village = place_key(first.village_name) == place_key(second.village_name)
    same_district = place_key(first.district) == place_key(second.district)
    description_similarity = _description_similarity(first.description, second.description)
    keyword_overlap, shared_keywords = _incident_keyword_overlap(
        first.description, second.description, category
    )

    # A same-village report needs a meaningful textual signal.  Reports from
    # different villages need a much stronger signal and the same district;
    # this avoids treating a common weather event as one confirmed incident.
    related = (
        same_village and (
            description_similarity >= 0.48
            or (keyword_overlap > 0 and description_similarity >= 0.30)
        )
    ) or (
        not same_village and same_district and keyword_overlap > 0
        and description_similarity >= 0.72
    )
    if not related:
        return None

    evidence = ["same AI-classified category", "reported within 48 hours"]
    evidence.append("same reported village" if same_village else "same reported district with strong description similarity")
    if shared_keywords:
        evidence.append("shared incident keywords: " + ", ".join(shared_keywords))
    evidence.append(f"description similarity {description_similarity:.0%}")
    return {"evidence": evidence, "score": description_similarity, "shared_keywords": shared_keywords}


def _verification_steps(category: str) -> list[str]:
    steps = [
        "Contact the listed reporters or village representative to verify the current situation and time.",
        "Record a field-team or authorised local update before treating reports as one incident.",
    ]
    if category in {"landslide", "road_blockage", "flood", "cloudburst"}:
        steps.append("Check safe access conditions with the responsible local authority; do not infer road or terrain status from these reports alone.")
    else:
        steps.append("Confirm the affected people, service interruption, and any immediate support already available.")
    return steps


def _authority_actions(category: str, severity: str) -> list[dict]:
    actions = [{"priority": 1, "action": "Assign an officer to verify the reports and log the verified outcome.", "basis": "Reports are related by local, category, time, and description signals; the relationship remains unconfirmed."}]
    if severity in {"HIGH", "CRITICAL"}:
        actions.append({"priority": len(actions) + 1, "action": "Alert the appropriate on-call response lead for review while verification is underway.", "basis": f"The highest recommended severity is {severity}, based on reported content and deterministic rules."})
    if category in {"landslide", "road_blockage", "flood", "cloudburst"}:
        actions.append({"priority": len(actions) + 1, "action": "Request a safe access and hazard-status check from the relevant local response authority.", "basis": "The reports describe a transport, weather, or terrain-related category; no route or hazard status is assumed."})
    else:
        actions.append({"priority": len(actions) + 1, "action": "Coordinate with the relevant local service lead after verification of the reported need.", "basis": "The response remains a recommendation pending human verification."})
    return actions


def build_incident_briefs(reports: list[CitizenReport]) -> list[dict]:
    """Fuse only strongly related citizen reports into *potential* incidents.

    Output intentionally separates database facts, inferred links, and response
    recommendations.  It never mutates reports or labels an event confirmed.
    """
    analyses = {report.public_id: _report_analysis(report) for report in reports}
    pairs: list[tuple[CitizenReport, CitizenReport, dict]] = []
    for index, first in enumerate(reports):
        for second in reports[index + 1:]:
            relationship = _relationship(first, second, analyses[first.public_id], analyses[second.public_id])
            if relationship:
                pairs.append((first, second, relationship))

    # Create compact cliques, not broad transitive components: every member
    # must relate to every other member in a group.
    groups: list[list[CitizenReport]] = []
    pair_lookup = {frozenset((first.public_id, second.public_id)): relationship for first, second, relationship in pairs}
    for first, second, _ in sorted(pairs, key=lambda pair: pair[2]["score"], reverse=True):
        candidate = [first, second]
        for report in reports:
            if report in candidate:
                continue
            if all(frozenset((report.public_id, member.public_id)) in pair_lookup for member in candidate):
                candidate.append(report)
        candidate_ids = {report.public_id for report in candidate}
        if not any(candidate_ids <= {report.public_id for report in group} for group in groups):
            groups.append(candidate)

    briefs = []
    for group in groups:
        group.sort(key=lambda report: report.submitted_at)
        categories = [analyses[report.public_id]["classification"]["predicted_category"] for report in group]
        category = Counter(categories).most_common(1)[0][0]
        highest_severity = max(
            (analyses[report.public_id]["severity"]["recommended_severity"] for report in group),
            key=lambda value: SEVERITY_ORDER[value],
        )
        villages = list(dict.fromkeys(normalise_place_name(report.village_name) for report in group))
        pair_evidence = []
        for first_index, first in enumerate(group):
            for second in group[first_index + 1:]:
                pair_evidence.extend(pair_lookup[frozenset((first.public_id, second.public_id))]["evidence"])
        facts = [
            f"{len(group)} citizen reports were submitted between {group[0].submitted_at.isoformat()} and {group[-1].submitted_at.isoformat()}.",
            "Reported villages: " + ", ".join(villages) + ".",
            "AI-classified category: " + category + ".",
        ]
        incident_id = "potential-" + "-".join(sorted(report.public_id for report in group)[:3])
        briefs.append({
            "incident_id": incident_id,
            "situation_summary": f"Potential {category.replace('_', ' ')} incident: {len(group)} related citizen reports require human review. This is not a confirmed incident.",
            "contributing_reports": [{
                "report_id": report.public_id, "village_name": normalise_place_name(report.village_name),
                "district": normalise_place_name(report.district), "description": report.description,
                "submitted_at": report.submitted_at,
                "reported_category": report.category,
                "ai_category": analyses[report.public_id]["classification"]["predicted_category"],
                "status": report.status,
                "photo_url": f"/api/v1/reports/{report.public_id}/photo" if report.photo_path else None,
            } for report in group],
            "affected_villages": villages,
            "highest_recommended_severity": highest_severity,
            "detected_facts": facts,
            "inferred_relationships": list(dict.fromkeys(pair_evidence)),
            "recommended_verification_steps": _verification_steps(category),
            "prioritized_authority_actions": _authority_actions(category, highest_severity),
        })
    return sorted(briefs, key=lambda brief: (-SEVERITY_ORDER[brief["highest_recommended_severity"]], brief["incident_id"]))
