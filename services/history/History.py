from typing import Dict, List

from bson import ObjectId
from fastapi import HTTPException

from app.db.db import survey_data_control_collection


def _normalize_need_status(document: Dict) -> str:
    raw_status = str(document.get("status") or "").strip().lower()
    if raw_status in {"pending", "assigned", "completed"}:
        return raw_status

    processing_status = str(document.get("processing_status") or "").strip().lower()
    if processing_status == "pending":
        return "pending"
    if processing_status == "processed":
        return "assigned"
    if processing_status == "completed":
        return "completed"

    return "pending"


def _normalize_ai_output(document: Dict) -> Dict:
    ai_analysis = document.get("ai_analysis", document.get("ai_need_output"))

    if not isinstance(ai_analysis, dict):
        ai_analysis = {}

    if "ai_analysis" in ai_analysis and isinstance(ai_analysis.get("ai_analysis"), dict):
        nested = ai_analysis["ai_analysis"]
        resources_raw = nested.get("resources", [])
        if not isinstance(resources_raw, list):
            resources_raw = []

        resources = [
            item.strip()
            for item in resources_raw
            if isinstance(item, str) and item.strip()
        ]

        urgency = str(nested.get("urgency") or "Unknown").strip().title()
        if urgency not in {"Low", "Medium", "High", "Critical", "Unknown"}:
            urgency = "Unknown"

        return {
            "description": str(ai_analysis.get("description") or "").strip(),
            "need_type": str(nested.get("need_type") or "Unknown").strip() or "Unknown",
            "urgency": urgency,
            "resources": list(dict.fromkeys(resources)),
        }

    resources_raw = ai_analysis.get("resources", ai_analysis.get("detected_needs", []))
    if not isinstance(resources_raw, list):
        resources_raw = []

    resources = [
        item.strip() for item in resources_raw if isinstance(item, str) and item.strip()
    ]

    urgency = str(
        ai_analysis.get("urgency") or ai_analysis.get("priority_level") or "Unknown"
    ).strip().title()
    if urgency not in {"Low", "Medium", "High", "Critical", "Unknown"}:
        urgency = "Unknown"

    return {
        "description": str(
            ai_analysis.get("description") or ai_analysis.get("short_summary") or ""
        ).strip(),
        "need_type": str(ai_analysis.get("need_type") or "Unknown").strip() or "Unknown",
        "urgency": urgency,
        "resources": list(dict.fromkeys(resources)),
    }


def _serialize_history_item(document: Dict) -> Dict:
    created_at = document.get("created_at")
    created_at_iso = created_at.isoformat() if created_at else ""

    return {
        "need_id": str(document["_id"]),
        "submitted_by": str(document.get("submitted_by") or ""),
        "location": document.get("location", ""),
        "people_affected": document.get("people_affected", "1-10"),
        "time_sensitivity": document.get("time_sensitivity", "Within a week"),
        "status": _normalize_need_status(document),
        "ai_output": _normalize_ai_output(document),
        "created_at": created_at_iso,
    }


async def get_history_needs(data, ngo_id: str) -> Dict:
    query: Dict = {"ngo_id": ngo_id}
    if data.submitted_by:
        query["submitted_by"] = data.submitted_by

    fetch_limit = max(data.limit * 5, 200)
    documents = (
        await survey_data_control_collection.find(query)
        .sort("created_at", -1)
        .limit(fetch_limit)
        .to_list(length=fetch_limit)
    )

    items: List[Dict] = [_serialize_history_item(document) for document in documents]

    if data.status:
        items = [item for item in items if item["status"] == data.status]

    return {
        "total": len(items),
        "items": items[: data.limit],
    }


async def get_history_need_by_id(need_id: str, ngo_id: str) -> Dict:
    if not ObjectId.is_valid(need_id):
        raise HTTPException(status_code=400, detail="Invalid need_id")

    document = await survey_data_control_collection.find_one(
        {
            "_id": ObjectId(need_id),
            "ngo_id": ngo_id,
        }
    )
    if not document:
        raise HTTPException(status_code=404, detail="Need not found")

    return _serialize_history_item(document)