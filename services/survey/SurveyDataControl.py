import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException

from app.db.db import survey_data_control_collection
from app.services.ai import analyze_survey_needs
from app.services.matching.VolunteerMatching import rank_volunteers_for_document


def _normalize_ai_analysis(ai_analysis):
    default_analysis = {
        "description": "Pending AI analysis",
        "need_type": "Unknown",
        "urgency": "Unknown",
        "resources": [],
    }

    if not isinstance(ai_analysis, dict):
        return default_analysis

    # Legacy nested shape support: {description, ai_analysis: {...}}
    if "ai_analysis" in ai_analysis and isinstance(ai_analysis.get("ai_analysis"), dict):
        nested = ai_analysis["ai_analysis"]
        resources = nested.get("resources", [])
        if not isinstance(resources, list):
            resources = []

        return {
            "description": str(ai_analysis.get("description") or "").strip(),
            "need_type": str(nested.get("need_type") or "Unknown").strip() or "Unknown",
            "urgency": str(nested.get("urgency") or "Unknown").strip().title() or "Unknown",
            "resources": [
                item.strip() for item in resources if isinstance(item, str) and item.strip()
            ],
        }

    # Legacy shape support: short_summary/detected_needs/priority_level
    resources = ai_analysis.get("resources", ai_analysis.get("detected_needs", []))
    if not isinstance(resources, list):
        resources = []

    return {
        "description": str(
            ai_analysis.get("description") or ai_analysis.get("short_summary") or ""
        ).strip(),
        "need_type": str(ai_analysis.get("need_type") or "Unknown").strip() or "Unknown",
        "urgency": str(
            ai_analysis.get("urgency") or ai_analysis.get("priority_level") or "Unknown"
        ).strip().title() or "Unknown",
        "resources": [item.strip() for item in resources if isinstance(item, str) and item.strip()],
    }


def _build_ai_output(document, ai_analysis):
    normalized_ai = _normalize_ai_analysis(ai_analysis)

    return {
        "submitted_by": str(document.get("submitted_by") or ""),
        "processing_status": str(document.get("processing_status") or "pending"),
        "location": document.get("location", ""),
        "need_type": normalized_ai["need_type"],
        "urgency": normalized_ai["urgency"],
        "people_affected": document.get("people_affected", "1-10"),
        "time_sensitivity": document.get("time_sensitivity", "Within a week"),
        "resources": normalized_ai["resources"],
        "status": {
            "urgency": normalized_ai["urgency"],
            "description": normalized_ai["description"],
        },
        "auto_match_result": _normalize_auto_match_result(document, normalized_ai),
    }


def _normalize_processing_status(value: Any) -> str:
    processing_status = str(value or "pending").strip().lower()
    if processing_status not in {"pending", "processed", "failed"}:
        return "pending"

    return processing_status


def _build_need_payload_for_match(document: Dict[str, Any], normalized_ai: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "need_id": str(document.get("_id") or document.get("need_id") or ""),
        "submitted_by": str(document.get("submitted_by") or ""),
        "need_type": normalized_ai["need_type"],
        "urgency": normalized_ai["urgency"],
        "resources": normalized_ai["resources"],
        "description": normalized_ai["description"]
        or str(document.get("description") or "No description available"),
        "location": str(document.get("location") or ""),
        "processing_status": _normalize_processing_status(document.get("processing_status")),
    }


def _build_default_auto_match_result(document: Dict[str, Any], normalized_ai: Dict[str, Any]) -> Dict[str, Any]:
    need_payload = _build_need_payload_for_match(document, normalized_ai)
    processing_status = need_payload["processing_status"]

    if processing_status == "failed":
        message = "Auto AI matching skipped because AI need analysis failed"
    elif processing_status == "processed":
        message = "Auto AI matching is in progress"
    else:
        message = "Auto AI matching is pending"

    return {
        "message": message,
        "total_volunteers_considered": 0,
        "need": need_payload,
        "ranked_volunteers": [],
    }


def _normalize_auto_match_result(document: Dict[str, Any], normalized_ai: Dict[str, Any]) -> Dict[str, Any]:
    auto_match_result = document.get("auto_match_result")

    if (
        isinstance(auto_match_result, dict)
        and isinstance(auto_match_result.get("need"), dict)
        and isinstance(auto_match_result.get("ranked_volunteers"), list)
        and isinstance(auto_match_result.get("total_volunteers_considered"), int)
    ):
        return auto_match_result

    return _build_default_auto_match_result(document, normalized_ai)


def _serialize_survey_data_control(document):
    ai_output = _build_ai_output(
        document,
        document.get("ai_analysis", document.get("ai_need_output")),
    )
    ai_output["created_at"] = document["created_at"].isoformat()

    return ai_output


async def _process_survey_ai(inserted_id, survey_data):
    try:
        ai_result = await analyze_survey_needs(survey_data)
        await survey_data_control_collection.update_one(
            {"_id": inserted_id},
            {
                "$set": {
                    "ai_analysis": ai_result,
                    "processing_status": "processed",
                    "processed_at": datetime.now(timezone.utc),
                }
            },
        )

        processed_document = await survey_data_control_collection.find_one({"_id": inserted_id})
        if not processed_document:
            return

        try:
            auto_match_result = await rank_volunteers_for_document(
                need_document=processed_document,
                ngo_id=str(survey_data.get("ngo_id") or ""),
                max_volunteers=50,
                max_ranked_results=10,
            )
        except Exception:
            auto_match_result = _build_default_auto_match_result(
                processed_document,
                _normalize_ai_analysis(processed_document.get("ai_analysis")),
            )
            auto_match_result["message"] = "Auto AI matching failed"

        await survey_data_control_collection.update_one(
            {"_id": inserted_id},
            {
                "$set": {
                    "auto_match_result": auto_match_result,
                    "auto_matched_at": datetime.now(timezone.utc),
                }
            },
        )
    except Exception:
        failed_ai_analysis = {
            "description": "AI analysis failed",
            "need_type": "Unknown",
            "urgency": "Unknown",
            "resources": [],
        }
        failed_document = {
            **survey_data,
            "_id": inserted_id,
            "processing_status": "failed",
            "ai_analysis": failed_ai_analysis,
        }

        await survey_data_control_collection.update_one(
            {"_id": inserted_id},
            {
                "$set": {
                    "ai_analysis": failed_ai_analysis,
                    "processing_status": "failed",
                    "processed_at": datetime.now(timezone.utc),
                    "auto_match_result": _build_default_auto_match_result(
                        failed_document,
                        _normalize_ai_analysis(failed_ai_analysis),
                    ),
                }
            },
        )


async def create_survey_data_control(data, ngo_id: str):
    survey_data = data.model_dump()
    survey_data["ngo_id"] = ngo_id
    survey_data["processing_status"] = "pending"
    survey_data["ai_analysis"] = {
        "description": "Pending AI analysis",
        "need_type": "Unknown",
        "urgency": "Unknown",
        "resources": [],
    }
    survey_data["created_at"] = datetime.now(timezone.utc)

    result = await survey_data_control_collection.insert_one(survey_data)
    survey_data["_id"] = result.inserted_id
    survey_data["auto_match_result"] = _build_default_auto_match_result(
        survey_data,
        _normalize_ai_analysis(survey_data["ai_analysis"]),
    )
    await survey_data_control_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"auto_match_result": survey_data["auto_match_result"]}},
    )

    asyncio.create_task(_process_survey_ai(result.inserted_id, survey_data.copy()))
    ai_output = _build_ai_output(survey_data, survey_data["ai_analysis"])

    return ai_output


async def get_survey_data_controls(limit: int, ngo_id: str):
    documents = (
        await survey_data_control_collection.find({"ngo_id": ngo_id})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )

    return {
        "total": len(documents),
        "items": [_serialize_survey_data_control(document) for document in documents],
    }


async def get_latest_survey_data_control_for_user(submitted_by: str, ngo_id: str):
    document = await survey_data_control_collection.find_one(
        {
            "submitted_by": submitted_by,
            "ngo_id": ngo_id,
        },
        sort=[("created_at", -1)],
    )

    if not document:
        raise HTTPException(status_code=404, detail="No survey need found for this user")

    return _build_ai_output(
        document,
        document.get("ai_analysis", document.get("ai_need_output")),
    )