from app.db.db import needs_collection, volunteers_collection


async def get_dashboard_summary():
    active_needs_query = {
        "$or": [
            {"status": "active"},
            {"status": "open"},
            {"is_active": True},
        ]
    }

    urgent_cases_query = {
        "$and": [
            active_needs_query,
            {
                "$or": [
                    {"priority": "urgent"},
                    {"urgency": "high"},
                    {"is_urgent": True},
                ]
            },
        ]
    }

    available_volunteers_query = {
        "$or": [
            {"is_available": True},
            {"status": "available"},
            {"availability": "available"},
        ]
    }

    total_active_needs = await needs_collection.count_documents(active_needs_query)
    urgent_cases = await needs_collection.count_documents(urgent_cases_query)
    available_volunteer_number = await volunteers_collection.count_documents(
        available_volunteers_query
    )

    return {
        "total_active_needs": total_active_needs,
        "available_volunteer_number": available_volunteer_number,
        "urgent_cases": urgent_cases,
        "auto_match_now_button": True,
    }


async def auto_match_now(data):
    active_needs_query = {
        "$or": [
            {"status": "active"},
            {"status": "open"},
            {"is_active": True},
        ]
    }

    available_volunteers_query = {
        "$or": [
            {"is_available": True},
            {"status": "available"},
            {"availability": "available"},
        ]
    }

    needs = await needs_collection.find(active_needs_query).limit(data.max_matches).to_list(
        length=data.max_matches
    )
    volunteers = await volunteers_collection.find(available_volunteers_query).limit(
        data.max_matches
    ).to_list(length=data.max_matches)

    matched_count = min(len(needs), len(volunteers))

    if data.dry_run:
        return {
            "message": "Auto-match simulation complete",
            "matched_count": matched_count,
            "dry_run": True,
        }

    for index in range(matched_count):
        need = needs[index]
        volunteer = volunteers[index]

        await needs_collection.update_one(
            {"_id": need["_id"]},
            {
                "$set": {
                    "status": "matched",
                    "matched_volunteer_id": volunteer["_id"],
                }
            },
        )

        await volunteers_collection.update_one(
            {"_id": volunteer["_id"]},
            {"$set": {"is_available": False}},
        )

    return {
        "message": "Auto-match completed",
        "matched_count": matched_count,
        "dry_run": False,
    }
