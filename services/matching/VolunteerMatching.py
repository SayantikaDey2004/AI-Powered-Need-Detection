import asyncio
import json
import re
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import HTTPException
from google import genai

from app.core.config import get_settings
from app.db.db import survey_data_control_collection, volunteers_collection


settings = get_settings()
client = genai.Client(api_key=settings.GENAI_API_KEY)

_ALLOWED_URGENCY = {"Low", "Medium", "High", "Critical", "Unknown"}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_text_list(values: List[str]) -> List[str]:
    return list(dict.fromkeys([value for value in values if value]))


def _normalize_ai_output(document: Dict[str, Any]) -> Dict[str, Any]:
    ai_analysis = document.get("ai_analysis", document.get("ai_need_output"))
    if not isinstance(ai_analysis, dict):
        ai_analysis = {}

    if "ai_analysis" in ai_analysis and isinstance(ai_analysis.get("ai_analysis"), dict):
        nested = ai_analysis["ai_analysis"]
        resources_raw = nested.get("resources", [])
        if not isinstance(resources_raw, list):
            resources_raw = []

        resources = _dedupe_text_list(
            [
                _normalize_text(item)
                for item in resources_raw
                if isinstance(item, str) and _normalize_text(item)
            ]
        )

        urgency = _normalize_text(nested.get("urgency") or "Unknown").title()
        if urgency not in _ALLOWED_URGENCY:
            urgency = "Unknown"

        return {
            "description": _normalize_text(ai_analysis.get("description")),
            "need_type": _normalize_text(nested.get("need_type") or "Unknown") or "Unknown",
            "urgency": urgency,
            "resources": resources,
        }

    resources_raw = ai_analysis.get("resources", ai_analysis.get("detected_needs", []))
    if not isinstance(resources_raw, list):
        resources_raw = []

    resources = _dedupe_text_list(
        [
            _normalize_text(item)
            for item in resources_raw
            if isinstance(item, str) and _normalize_text(item)
        ]
    )

    urgency = _normalize_text(
        ai_analysis.get("urgency") or ai_analysis.get("priority_level") or "Unknown"
    ).title()
    if urgency not in _ALLOWED_URGENCY:
        urgency = "Unknown"

    return {
        "description": _normalize_text(
            ai_analysis.get("description") or ai_analysis.get("short_summary")
        ),
        "need_type": _normalize_text(ai_analysis.get("need_type") or "Unknown") or "Unknown",
        "urgency": urgency,
        "resources": resources,
    }


def _extract_need_payload(document: Dict[str, Any]) -> Dict[str, Any]:
    ai_output = _normalize_ai_output(document)
    processing_status = _normalize_text(document.get("processing_status") or "pending").lower()
    if processing_status not in {"pending", "processed", "failed"}:
        processing_status = "pending"

    return {
        "need_id": _normalize_text(document.get("_id") or document.get("need_id")),
        "submitted_by": _normalize_text(document.get("submitted_by")),
        "need_type": ai_output["need_type"],
        "urgency": ai_output["urgency"],
        "resources": ai_output["resources"],
        "description": ai_output["description"]
        or _normalize_text(document.get("description") or "No description available"),
        "location": _normalize_text(document.get("location")),
        "processing_status": processing_status,
    }


def _extract_skills(volunteer: Dict[str, Any]) -> List[str]:
    raw_sources = [
        volunteer.get("skills"),
        volunteer.get("skill"),
        volunteer.get("expertise"),
        volunteer.get("domains"),
    ]

    skills: List[str] = []
    for source in raw_sources:
        if isinstance(source, list):
            skills.extend([_normalize_text(item) for item in source if _normalize_text(item)])
        elif isinstance(source, str) and _normalize_text(source):
            skills.extend(
                [
                    _normalize_text(part)
                    for part in re.split(r"[,/|]", source)
                    if _normalize_text(part)
                ]
            )

    return _dedupe_text_list(skills)


def _extract_volunteer_location(volunteer: Dict[str, Any]) -> str:
    raw_location = volunteer.get("location")
    if not raw_location:
        raw_location = volunteer.get("address")

    if isinstance(raw_location, dict):
        location_parts = [
            _normalize_text(raw_location.get("area")),
            _normalize_text(raw_location.get("city")),
            _normalize_text(raw_location.get("district")),
            _normalize_text(raw_location.get("state")),
            _normalize_text(raw_location.get("country")),
        ]
        combined_location = ", ".join([part for part in location_parts if part])
        return _normalize_text(combined_location)

    candidate_fields = [
        raw_location,
        volunteer.get("city"),
        volunteer.get("city_area"),
        volunteer.get("district"),
        volunteer.get("state"),
        volunteer.get("pin_code"),
    ]
    normalized_fields = [_normalize_text(value) for value in candidate_fields if _normalize_text(value)]
    return ", ".join(_dedupe_text_list(normalized_fields))


def _normalize_volunteer(volunteer: Dict[str, Any]) -> Dict[str, Any]:
    volunteer_id = _normalize_text(
        volunteer.get("_id") or volunteer.get("volunteer_id") or volunteer.get("user_id")
    )

    return {
        "volunteer_id": volunteer_id,
        "volunteer_name": _normalize_text(
            volunteer.get("name")
            or volunteer.get("full_name")
            or volunteer.get("volunteer_name")
            or "Unknown Volunteer"
        ),
        "volunteer_email": _normalize_text(
            volunteer.get("email") or volunteer.get("volunteer_email")
        )
        or None,
        "volunteer_phone": _normalize_text(
            volunteer.get("phone")
            or volunteer.get("phone_number")
            or volunteer.get("mobile")
            or volunteer.get("volunteer_phone")
        )
        or None,
        "volunteer_location": _extract_volunteer_location(volunteer) or None,
        "skills": _extract_skills(volunteer),
    }


def _to_score(value: Any) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = 0

    return max(0, min(score, 100))


def _safe_parse_ranked_text(raw_text: str) -> List[Dict[str, Any]]:
    text = _normalize_text(raw_text)
    if not text:
        return []

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    ranked_items = parsed.get("ranked_volunteers") if isinstance(parsed, dict) else []
    if not isinstance(ranked_items, list):
        return []

    cleaned_items: List[Dict[str, Any]] = []
    for item in ranked_items:
        if not isinstance(item, dict):
            continue

        volunteer_id = _normalize_text(item.get("volunteer_id"))
        if not volunteer_id:
            continue

        cleaned_items.append(
            {
                "volunteer_id": volunteer_id,
                "score": _to_score(item.get("score")),
                "explanation": _normalize_text(item.get("explanation"))
                or "Selected by AI ranking",
            }
        )

    return cleaned_items


def _build_match_prompt(need: Dict[str, Any], volunteers: List[Dict[str, Any]], top_k: int) -> str:
    payload = {
        "need": {
            "need_id": need["need_id"],
            "need_type": need["need_type"],
            "urgency": need["urgency"],
            "resources": need["resources"],
            "description": need["description"],
            "location": need["location"],
        },
        "volunteers": [
            {
                "volunteer_id": volunteer["volunteer_id"],
                "volunteer_name": volunteer["volunteer_name"],
                "location": volunteer["volunteer_location"],
                "skills": volunteer["skills"],
            }
            for volunteer in volunteers
        ],
    }

    return (
        "You are an NGO volunteer matching assistant. "
        "Rank volunteers for the need using location proximity, skill relevance, urgency fit, and practical suitability. "
        "Return JSON only with this exact shape: "
        "{\"ranked_volunteers\": [{\"volunteer_id\": string, \"score\": number, \"explanation\": string}]}. "
        f"Return at most {top_k} volunteers. "
        "Use score from 0 to 100. "
        "Do not include volunteers not listed in input.\n\n"
        f"Input payload:\n{json.dumps(payload, ensure_ascii=True)}"
    )


def _fallback_rank_volunteers(need: Dict[str, Any], volunteers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    need_tokens = set(
        re.findall(
            r"[a-z0-9]+",
            " ".join(
                [need.get("need_type", ""), need.get("description", "")] + need.get("resources", [])
            ).lower(),
        )
    )

    ranked: List[Dict[str, Any]] = []
    need_location_tokens = set(re.findall(r"[a-z0-9]+", _normalize_text(need.get("location")).lower()))

    for volunteer in volunteers:
        skill_tokens = set(re.findall(r"[a-z0-9]+", " ".join(volunteer["skills"]).lower()))
        location_tokens = set(
            re.findall(
                r"[a-z0-9]+",
                _normalize_text(volunteer.get("volunteer_location")).lower(),
            )
        )

        skill_overlap = len(need_tokens.intersection(skill_tokens))
        location_overlap = len(need_location_tokens.intersection(location_tokens))
        score = min(100, 30 + skill_overlap * 12 + location_overlap * 14)

        if skill_overlap >= 3 and location_overlap >= 1:
            explanation = "Strong skill overlap and nearby location match"
        elif skill_overlap >= 1 and location_overlap >= 1:
            explanation = "Good skill overlap with location alignment"
        elif skill_overlap >= 1:
            explanation = "Moderate skill overlap with this need"
        elif location_overlap >= 1:
            explanation = "Location match with limited direct skill overlap"
        else:
            explanation = "General volunteer availability with limited direct overlap"

        ranked.append(
            {
                **volunteer,
                "score": score,
                "explanation": explanation,
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def _apply_ai_rank(
    need: Dict[str, Any],
    volunteers: List[Dict[str, Any]],
    ai_ranked_items: List[Dict[str, Any]],
    max_ranked_results: int,
) -> List[Dict[str, Any]]:
    volunteer_index = {item["volunteer_id"]: item for item in volunteers}

    ranked: List[Dict[str, Any]] = []
    seen_ids = set()

    for ai_item in ai_ranked_items:
        volunteer = volunteer_index.get(ai_item["volunteer_id"])
        if not volunteer:
            continue
        if volunteer["volunteer_id"] in seen_ids:
            continue

        ranked.append(
            {
                **volunteer,
                "score": _to_score(ai_item.get("score")),
                "explanation": _normalize_text(ai_item.get("explanation"))
                or "Selected by AI ranking",
            }
        )
        seen_ids.add(volunteer["volunteer_id"])

        if len(ranked) >= max_ranked_results:
            return ranked

    fallback_ranked = _fallback_rank_volunteers(need, volunteers)
    for fallback_item in fallback_ranked:
        volunteer_id = fallback_item["volunteer_id"]
        if volunteer_id in seen_ids:
            continue

        ranked.append(fallback_item)
        seen_ids.add(volunteer_id)

        if len(ranked) >= max_ranked_results:
            break

    return ranked


async def _fetch_need_document(data, ngo_id: str) -> Dict[str, Any]:
    if data.need_id:
        query_or: List[Dict[str, Any]] = [{"need_id": data.need_id}, {"_id": data.need_id}]
        if ObjectId.is_valid(data.need_id):
            query_or.insert(0, {"_id": ObjectId(data.need_id)})

        document = await survey_data_control_collection.find_one(
            {
                "$and": [
                    {"ngo_id": ngo_id},
                    {"$or": query_or},
                ]
            }
        )
    else:
        document = await survey_data_control_collection.find_one(
            {
                "ngo_id": ngo_id,
                "submitted_by": data.submitted_by,
            },
            sort=[("created_at", -1)],
        )

    if not document:
        raise HTTPException(status_code=404, detail="Need not found")

    processing_status = _normalize_text(document.get("processing_status")).lower()
    if processing_status != "processed":
        raise HTTPException(
            status_code=400,
            detail="AI output is not ready for this need yet",
        )

    if not isinstance(document.get("ai_analysis", document.get("ai_need_output")), dict):
        raise HTTPException(status_code=400, detail="AI output is missing for this need")

    return document


async def _fetch_available_volunteers(ngo_id: str, max_volunteers: int) -> List[Dict[str, Any]]:
    available_query = {
        "$or": [
            {"is_available": True},
            {"status": "available"},
            {"availability": "available"},
        ]
    }

    scoped_query = {
        "$and": [
            available_query,
            {
                "$or": [
                    {"ngo_id": ngo_id},
                    {"ngoId": ngo_id},
                    {"organization_id": ngo_id},
                    {"organizationId": ngo_id},
                ]
            },
        ]
    }

    documents = await volunteers_collection.find(scoped_query).limit(max_volunteers).to_list(
        length=max_volunteers
    )

    if not documents:
        legacy_global_query = {
            "$and": [
                available_query,
                {"ngo_id": {"$exists": False}},
                {"ngoId": {"$exists": False}},
                {"organization_id": {"$exists": False}},
                {"organizationId": {"$exists": False}},
            ]
        }
        documents = await volunteers_collection.find(legacy_global_query).limit(
            max_volunteers
        ).to_list(length=max_volunteers)

    normalized = [_normalize_volunteer(document) for document in documents]
    return [item for item in normalized if item["volunteer_id"]]


def _rank_volunteers_with_gemini(
    need: Dict[str, Any], volunteers: List[Dict[str, Any]], max_ranked_results: int
) -> List[Dict[str, Any]]:
    prompt = _build_match_prompt(need, volunteers, max_ranked_results)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return _safe_parse_ranked_text(getattr(response, "text", ""))


async def rank_volunteers_for_document(
    need_document: Dict[str, Any],
    ngo_id: str,
    max_volunteers: int = 50,
    max_ranked_results: int = 10,
) -> Dict[str, Any]:
    need = _extract_need_payload(need_document)

    volunteers = await _fetch_available_volunteers(ngo_id, max_volunteers)
    if not volunteers:
        return {
            "message": "No available volunteers found for this NGO",
            "total_volunteers_considered": 0,
            "need": need,
            "ranked_volunteers": [],
        }

    try:
        ai_ranked_items = await asyncio.to_thread(
            _rank_volunteers_with_gemini,
            need,
            volunteers,
            max_ranked_results,
        )
    except Exception:
        ai_ranked_items = []

    if ai_ranked_items:
        ranked_volunteers = _apply_ai_rank(
            need,
            volunteers,
            ai_ranked_items,
            max_ranked_results,
        )
        message = "Volunteers ranked successfully using AI"
    else:
        ranked_volunteers = _fallback_rank_volunteers(need, volunteers)[:max_ranked_results]
        message = "Volunteers ranked using fallback logic (AI unavailable)"

    return {
        "message": message,
        "total_volunteers_considered": len(volunteers),
        "need": need,
        "ranked_volunteers": ranked_volunteers,
    }


async def rank_volunteers_for_need(data, ngo_id: str) -> Dict[str, Any]:
    need_document = await _fetch_need_document(data, ngo_id)
    return await rank_volunteers_for_document(
        need_document=need_document,
        ngo_id=ngo_id,
        max_volunteers=data.max_volunteers,
        max_ranked_results=data.max_ranked_results,
    )
