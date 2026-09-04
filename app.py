from datetime import date

from flask import Flask, jsonify, render_template, request

from model import RecoveryPatternModel, analyze_entry


app = Flask(__name__)
model = RecoveryPatternModel()


CORE_FIELDS = [
    "headache",
    "dizziness",
    "sleep",
    "screen_tolerance",
    "concentration",
    "activity",
]


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

def clamp_score(value, default=5):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    return max(0, min(10, value))


def clean_text(value, limit=1000):
    if value is None:
        return ""

    return str(value).strip()[:limit]


def clean_date(value):
    value = clean_text(value, 10)

    try:
        date.fromisoformat(value)
        return value
    except (TypeError, ValueError):
        return date.today().isoformat()


def clean_optional_date(value):
    value = clean_text(value, 10)

    if not value:
        return ""

    try:
        date.fromisoformat(value)
        return value
    except (TypeError, ValueError):
        return ""


def clean_saved_notes(value):
    if not isinstance(value, list):
        return []

    output = []

    for item in value[:20]:
        if not isinstance(item, dict):
            continue

        text = clean_text(
            item.get("text"),
            500,
        )

        if not text:
            continue

        output.append(
            {
                "text": text,
                "start": clean_optional_date(
                    item.get("start")
                ),
            }
        )

    return output


def clean_tracked_symptoms(value):
    if not isinstance(value, list):
        return []

    output = []

    for item in value[:30]:
        if not isinstance(item, dict):
            continue

        symptom_id = clean_text(
            item.get("id"),
            80,
        )

        name = clean_text(
            item.get("name"),
            100,
        )

        if not symptom_id or not name:
            continue

        direction = item.get("direction")

        if direction not in (
            "better",
            "worse",
        ):
            direction = "worse"

        output.append(
            {
                "id": symptom_id,
                "name": name,
                "value": clamp_score(
                    item.get("value")
                ),
                "direction": direction,
            }
        )

    return output


def clean_symptom_durations(value):
    if not isinstance(value, dict):
        return {}

    output = {}

    for symptom_id, item in list(
        value.items()
    )[:30]:

        if not isinstance(item, dict):
            continue

        clean_id = clean_text(
            symptom_id,
            80,
        )

        if not clean_id:
            continue

        output[clean_id] = {
            "name": clean_text(
                item.get("name"),
                100,
            ),
            "start": clean_optional_date(
                item.get("start")
            ),
            "duration": clean_text(
                item.get("duration"),
                100,
            ),
        }

    return output


def clean_red_flags(value):
    if not isinstance(value, list):
        return []

    return [
        clean_text(item, 80)
        for item in value[:20]
        if isinstance(item, str)
    ]


# ---------------------------------------------------------
# CHECK-IN CLEANING
# ---------------------------------------------------------

def clean_entry(payload, day_number=1):
    if not isinstance(payload, dict):
        payload = {}

    core_values = {
        key: clamp_score(
            payload.get(key)
        )
        for key in CORE_FIELDS
    }

    saved_notes = clean_saved_notes(
        payload.get("saved_notes")
    )

    notes_text = clean_text(
        payload.get("notes"),
        1500,
    )

    if (
        not notes_text
        and saved_notes
    ):
        notes_text = "; ".join(
            item["text"]
            for item in saved_notes
        )[:1500]

    return {
        "day": day_number,
        "checkin_date": clean_date(
            payload.get("checkin_date")
        ),
        **core_values,
        "notes": notes_text,
        "saved_notes": saved_notes,
        "tracked_symptoms":
            clean_tracked_symptoms(
                payload.get(
                    "tracked_symptoms"
                )
            ),
        "symptom_durations":
            clean_symptom_durations(
                payload.get(
                    "symptom_durations"
                )
            ),
        "safety_notes": clean_text(
            payload.get("safety_notes"),
            1000,
        ),
        "urgent_change": bool(
            payload.get("urgent_change")
        ),
        "red_flags": clean_red_flags(
            payload.get("red_flags")
        ),
    }


def clean_history(value):
    """
    Validate recovery history supplied by the browser.

    RecoverPath does not maintain a global server-side health
    record. The browser owns the user's stored recovery history
    and sends the minimum history needed for analysis.
    """

    if not isinstance(value, list):
        return []

    cleaned = []

    # Limit the amount accepted in a single request.
    for payload in value[-365:]:
        if not isinstance(payload, dict):
            continue

        cleaned.append(
            clean_entry(
                payload,
                len(cleaned) + 1,
            )
        )

    return cleaned


# ---------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------

def analyze_history(entries):
    results = []

    for index, entry in enumerate(entries):
        history = entries[: index + 1]

        analysis = analyze_entry(
            entry,
            history,
            model,
        )

        results.append(
            {
                **entry,
                **analysis,
            }
        )

    return results


def build_insights(data):
    if not data:
        return [
            (
                "Complete a check-in to begin "
                "identifying recovery patterns."
            )
        ]

    latest = data[-1]

    intelligence = latest.get(
        "recovery_intelligence",
        {},
    )

    symptom_data = latest.get(
        "symptom_insights",
        {},
    )

    output = []

    recovery_score = intelligence.get(
        "recovery_score"
    )

    if recovery_score is not None:
        output.append(
            "Descriptive recovery score: "
            f"{recovery_score}/100."
        )

    if len(data) >= 2:
        first_burden = data[0][
            "burden_score"
        ]

        latest_burden = data[-1][
            "burden_score"
        ]

        change = round(
            latest_burden
            - first_burden,
            2,
        )

        if change < 0:
            output.append(
                "Calculated symptom burden "
                f"decreased by {abs(change)} "
                "points across the selected "
                "recorded history."
            )

        elif change > 0:
            output.append(
                "Calculated symptom burden "
                f"increased by {change} "
                "points across the selected "
                "recorded history."
            )

        else:
            output.append(
                "Calculated symptom burden "
                "remained stable across the "
                "selected recorded history."
            )

    most_improved = symptom_data.get(
        "most_improved"
    )

    if most_improved:
        output.append(
            "Most improved core recovery "
            "indicator since the previous "
            f"check-in: {most_improved}."
        )

    most_worsened = symptom_data.get(
        "most_worsened"
    )

    if most_worsened:
        output.append(
            "Most worsened core recovery "
            "indicator since the previous "
            f"check-in: {most_worsened}."
        )

    needs_attention = symptom_data.get(
        "needs_attention"
    )

    if needs_attention:
        output.append(
            "Core recovery indicator currently "
            "carrying the highest calculated "
            f"burden: {needs_attention}."
        )

    triggers = latest.get(
        "triggers",
        [],
    )

    if triggers:
        strongest = triggers[0]

        output.append(
            "Most frequently detected possible "
            "trigger in recent notes: "
            f"{strongest['name']} "
            f"({strongest['mentions']} recent "
            "mention(s))."
        )
    else:
        output.append(
            "No repeated trigger pattern has "
            "been identified from recent notes."
        )

    consistency = intelligence.get(
        "consistency"
    )

    if consistency is not None:
        output.append(
            "Recovery consistency score: "
            f"{consistency}/100."
        )

    return output


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template(
        "index.html"
    )


@app.route(
    "/api/entry",
    methods=["POST"],
)
def analyze_checkin():
    payload = request.get_json(
        force=True,
        silent=True,
    )

    if not isinstance(payload, dict):
        return jsonify(
            {
                "error":
                    "Invalid check-in data."
            }
        ), 400

    history = clean_history(
        payload.get(
            "history",
            [],
        )
    )

    current_payload = payload.get(
        "entry"
    )

    # Temporary compatibility with the existing frontend.
    # Until index.html is updated, a normal check-in payload
    # can still be posted directly to /api/entry.
    if not isinstance(
        current_payload,
        dict,
    ):
        current_payload = {
            key: value
            for key, value
            in payload.items()
            if key != "history"
        }

    current = clean_entry(
        current_payload,
        len(history) + 1,
    )

    analysis_history = [
        *history,
        current,
    ]

    analysis = analyze_entry(
        current,
        analysis_history,
        model,
    )

    return jsonify(
        {
            **current,
            **analysis,
        }
    )


@app.route(
    "/api/analyze-history",
    methods=["POST"],
)
def analyze_saved_history():
    payload = request.get_json(
        force=True,
        silent=True,
    )

    if not isinstance(payload, dict):
        return jsonify(
            {
                "error":
                    "Invalid recovery history."
            }
        ), 400

    history = clean_history(
        payload.get(
            "history",
            [],
        )
    )

    data = analyze_history(
        history
    )

    return jsonify(
        {
            "entries": data,
            "latest": (
                data[-1]
                if data
                else None
            ),
            "insights":
                build_insights(data),
        }
    )


@app.route("/api/status")
def status():
    """
    No personal recovery data is stored globally on the server.

    This endpoint remains available so the current frontend keeps
    working during the transition to browser-owned history.
    """

    return jsonify(
        {
            "entries": [],
            "latest": None,
            "insights": [
                (
                    "Your recovery history is "
                    "stored in this browser."
                )
            ],
            "storage": {
                "server_health_history":
                    False,
                "browser_owned_history":
                    True,
            },
            "responsible_ai": {
                "model": (
                    "Random Forest classifier "
                    "trained on synthetic "
                    "demonstration data."
                ),
                "ml_role": (
                    "The model classifies changes "
                    "in six defined self-reported "
                    "recovery indicators."
                ),
                "safety_role": (
                    "Safety logic is deterministic "
                    "and separate from ML."
                ),
                "privacy": (
                    "The application is designed "
                    "so personal recovery history "
                    "does not need to be retained "
                    "in a shared server-side "
                    "health record."
                ),
                "limitations": (
                    "RecoverPath AI does not "
                    "diagnose concussion, predict "
                    "clinical outcomes, or replace "
                    "professional care."
                ),
            },
        }
    )


@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "RecoverPath AI",
            "server_health_records": 0,
            "storage_mode":
                "browser_owned_history",
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
