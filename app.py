from datetime import date
from flask import Flask, render_template, request, jsonify
from model import RecoveryPatternModel, analyze_entry

app = Flask(__name__)
model = RecoveryPatternModel()


# -------------------------------------------------------------------
# DEMO DATA
# -------------------------------------------------------------------
# These initial entries make the hackathon demo useful immediately.
# In the next persistence step, real user entries will be stored
# separately instead of relying only on process memory.
# -------------------------------------------------------------------

entries = [
    {
        "day": 1,
        "checkin_date": "2026-09-01",
        "headache": 7,
        "dizziness": 6,
        "sleep": 4,
        "screen_tolerance": 3,
        "concentration": 7,
        "activity": 2,
        "notes": (
            "Resting most of the day after significant screen exposure."
        ),
        "saved_notes": [],
        "tracked_symptoms": [],
        "symptom_durations": {},
        "safety_notes": "",
        "red_flags": [],
    },
    {
        "day": 2,
        "checkin_date": "2026-09-02",
        "headache": 6,
        "dizziness": 5,
        "sleep": 5,
        "screen_tolerance": 4,
        "concentration": 6,
        "activity": 3,
        "notes": (
            "Slight improvement after reducing screen time."
        ),
        "saved_notes": [],
        "tracked_symptoms": [],
        "symptom_durations": {},
        "safety_notes": "",
        "red_flags": [],
    },
    {
        "day": 3,
        "checkin_date": "2026-09-03",
        "headache": 5,
        "dizziness": 4,
        "sleep": 6,
        "screen_tolerance": 5,
        "concentration": 5,
        "activity": 4,
        "notes": (
            "Could tolerate a short walk and some reading."
        ),
        "saved_notes": [],
        "tracked_symptoms": [],
        "symptom_durations": {},
        "safety_notes": "",
        "red_flags": [],
    },
]


CORE_FIELDS = [
    "headache",
    "dizziness",
    "sleep",
    "screen_tolerance",
    "concentration",
    "activity",
]


# -------------------------------------------------------------------
# VALIDATION HELPERS
# -------------------------------------------------------------------

def clamp_score(value, default=5):
    """
    Convert a symptom score to an integer between 0 and 10.
    """

    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    return max(0, min(10, value))


def clean_text(value, limit=1000):
    """
    Store user-entered text safely as plain text and limit its size.
    """

    if value is None:
        return ""

    return str(value).strip()[:limit]


def clean_date(value):
    """
    Accept ISO YYYY-MM-DD dates.

    Invalid values fall back to today's date.
    """

    value = clean_text(value, 10)

    try:
        date.fromisoformat(value)
        return value
    except (TypeError, ValueError):
        return date.today().isoformat()


def clean_optional_date(value):
    """
    Validate an optional ISO date.
    """

    value = clean_text(value, 10)

    if not value:
        return ""

    try:
        date.fromisoformat(value)
        return value
    except (TypeError, ValueError):
        return ""


def clean_saved_notes(value):
    """
    Preserve the structured notes sent by the new frontend.
    """

    if not isinstance(value, list):
        return []

    output = []

    for item in value[:20]:
        if not isinstance(item, dict):
            continue

        text = clean_text(item.get("text"), 500)

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
    """
    Custom symptoms are tracked as additional context.

    The Random Forest still uses the six defined core inputs because
    those are the features on which the prototype model was trained.
    """

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

        if direction not in ("better", "worse"):
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
    """
    Preserve symptom start dates and frontend-calculated duration labels.
    """

    if not isinstance(value, dict):
        return {}

    output = {}

    for symptom_id, item in list(value.items())[:30]:
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


# -------------------------------------------------------------------
# RECOVERY DATA
# -------------------------------------------------------------------

def enriched():
    """
    Run every stored entry through the recovery-pattern model.

    The model receives the chronological history available up to
    that entry.
    """

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


# -------------------------------------------------------------------
# PATTERN INSIGHTS
# -------------------------------------------------------------------

def build_insights(data):
    if not data:
        return [
            "Complete a check-in to begin identifying recovery patterns."
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
            f"Recovery Intelligence Score: "
            f"{recovery_score}/100."
        )

    if len(data) >= 2:
        first_burden = data[0]["burden_score"]
        latest_burden = data[-1]["burden_score"]

        change = round(
            latest_burden - first_burden,
            2,
        )

        if change < 0:
            output.append(
                "Overall calculated symptom burden "
                f"decreased by {abs(change)} points "
                f"between Day {data[0]['day']} "
                f"and Day {data[-1]['day']}."
            )

        elif change > 0:
            output.append(
                "Overall calculated symptom burden "
                f"increased by {change} points "
                f"between Day {data[0]['day']} "
                f"and Day {data[-1]['day']}."
            )

        else:
            output.append(
                "Overall calculated symptom burden "
                "remained stable across the recorded period."
            )

    most_improved = symptom_data.get(
        "most_improved"
    )

    if most_improved:
        output.append(
            "Most improved core recovery indicator "
            f"since the previous entry: {most_improved}."
        )

    needs_attention = symptom_data.get(
        "needs_attention"
    )

    if needs_attention:
        output.append(
            "Core recovery indicator currently carrying "
            f"the highest calculated burden: {needs_attention}."
        )

    triggers = latest.get(
        "triggers",
        [],
    )

    if triggers:
        strongest = triggers[0]

        output.append(
            "Most frequently detected possible trigger "
            f"in recent notes: {strongest['name']} "
            f"({strongest['mentions']} recent mention(s))."
        )
    else:
        output.append(
            "No repeated trigger pattern has been identified "
            "from recent notes yet."
        )

    consistency = intelligence.get(
        "consistency"
    )

    if consistency is not None:
        output.append(
            f"Recovery consistency score: "
            f"{consistency}/100."
        )

    return output


# -------------------------------------------------------------------
# SUMMARY
# -------------------------------------------------------------------

def build_recovery_summary(data):
    """
    Produce a plain-language summary of the stored recovery history.

    This is a record summary, not a diagnosis.
    """

    if not data:
        return "No recovery entries recorded yet."

    latest = data[-1]
    first = data[0]

    lines = [
        "RECOVERPATH AI — RECOVERY HISTORY SUMMARY",
        "",
        f"Entries analyzed: {len(data)}",
        (
            "Latest check-in date: "
            f"{latest.get('checkin_date', 'Not recorded')}"
        ),
        (
            "Current recovery pattern: "
            f"{latest['pattern'].replace('_', ' ')}"
        ),
        (
            "Current calculated symptom burden: "
            f"{latest['burden_score']}/10"
        ),
        (
            "Burden change: "
            f"{first['burden_score']}/10 "
            f"→ {latest['burden_score']}/10"
        ),
        "",
        "LATEST CORE RECOVERY INDICATORS",
        f"Headache: {latest['headache']}/10",
        f"Dizziness: {latest['dizziness']}/10",
        f"Sleep quality: {latest['sleep']}/10",
        (
            "Screen tolerance: "
            f"{latest['screen_tolerance']}/10"
        ),
        (
            "Concentration difficulty: "
            f"{latest['concentration']}/10"
        ),
        (
            "Activity tolerance: "
            f"{latest['activity']}/10"
        ),
    ]

    tracked = latest.get(
        "tracked_symptoms",
        [],
    )

    core_ids = set(CORE_FIELDS)

    custom = [
        item
        for item in tracked
        if item.get("id") not in core_ids
    ]

    if custom:
        lines.extend(
            [
                "",
                "ADDITIONAL TRACKED SYMPTOMS",
            ]
        )

        for item in custom:
            lines.append(
                f"- {item['name']}: "
                f"{item['value']}/10"
            )

    durations = latest.get(
        "symptom_durations",
        {},
    )

    recorded_durations = [
        item
        for item in durations.values()
        if item.get("start")
    ]

    if recorded_durations:
        lines.extend(
            [
                "",
                "SYMPTOM DURATION CONTEXT",
            ]
        )

        for item in recorded_durations:
            lines.append(
                f"- {item.get('name', 'Symptom')}: "
                f"started {item['start']}"
                + (
                    f" ({item['duration']})"
                    if item.get("duration")
                    else ""
                )
            )

    notes = latest.get(
        "saved_notes",
        [],
    )

    if notes:
        lines.extend(
            [
                "",
                "LATEST NOTES / POSSIBLE TRIGGERS",
            ]
        )

        for note in notes:
            text = note.get("text", "")

            if not text:
                continue

            line = f"- {text}"

            if note.get("start"):
                line += (
                    f" — started {note['start']}"
                )

            lines.append(line)

    safety_notes = latest.get(
        "safety_notes",
        "",
    )

    if safety_notes:
        lines.extend(
            [
                "",
                "REPORTED NEW OR WORSENING CHANGE",
                safety_notes,
            ]
        )

    if latest.get("safety", {}).get("urgent"):
        lines.extend(
            [
                "",
                "SAFETY NOTICE",
                (
                    "Rule-based safety criteria were triggered "
                    "for the latest entry."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "RESPONSIBLE AI NOTICE",
            (
                "Machine learning is used to classify changes "
                "in the six defined core recovery indicators."
            ),
            (
                "Additional custom symptoms are stored as "
                "tracking context and are not silently treated "
                "as model-training features."
            ),
            (
                "Emergency safety decisions are kept separate "
                "from the machine-learning prediction."
            ),
            (
                "This information is based on self-reported data "
                "and is not a diagnosis or clinical assessment."
            ),
        ]
    )

    return "\n".join(lines)


# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/status")
def status():
    data = enriched()

    latest = (
        data[-1]
        if data
        else None
    )

    return jsonify(
        entries=data,
        latest=latest,
        insights=build_insights(data),
        recovery_summary=build_recovery_summary(data),
        responsible_ai={
            "model": (
                "Random Forest classifier trained on synthetic "
                "demonstration data."
            ),
            "ml_role": (
                "The model classifies changes in six defined "
                "self-reported recovery indicators as improving, "
                "stable, or a possible setback."
            ),
            "custom_symptoms": (
                "User-added symptoms are preserved as additional "
                "tracking context and are not automatically treated "
                "as trained ML features."
            ),
            "safety_role": (
                "Emergency safety logic is deterministic and "
                "separate from ML predictions."
            ),
            "limitations": (
                "RecoverPath AI does not diagnose concussion, "
                "determine medical seriousness, predict clinical "
                "outcomes, or replace professional care."
            ),
        },
    )


@app.route("/api/entry", methods=["POST"])
def add_entry():
    payload = request.get_json(
        force=True,
        silent=True,
    )

    if not isinstance(payload, dict):
        return jsonify(
            {
                "error": "Invalid check-in data."
            }
        ), 400

    core_values = {
        key: clamp_score(
            payload.get(key)
        )
        for key in CORE_FIELDS
    }

    saved_notes = clean_saved_notes(
        payload.get("saved_notes")
    )

    # Keep a plain notes string because model.py uses recent note text
    # for its simple possible-trigger detection.
    notes_text = clean_text(
        payload.get("notes"),
        1500,
    )

    if not notes_text and saved_notes:
        notes_text = "; ".join(
            item["text"]
            for item in saved_notes
        )[:1500]

    urgent_change = bool(
        payload.get("urgent_change")
    )

    safety_notes = clean_text(
        payload.get("safety_notes"),
        1000,
    )

    red_flags = payload.get(
        "red_flags",
        [],
    )

    if not isinstance(red_flags, list):
        red_flags = []

    # Keep only known string identifiers supplied by the client.
    red_flags = [
        clean_text(item, 80)
        for item in red_flags[:20]
        if isinstance(item, str)
    ]

    entry = {
        "day": len(entries) + 1,
        "checkin_date": clean_date(
            payload.get("checkin_date")
        ),
        **core_values,
        "notes": notes_text,
        "saved_notes": saved_notes,
        "tracked_symptoms": clean_tracked_symptoms(
            payload.get("tracked_symptoms")
        ),
        "symptom_durations": clean_symptom_durations(
            payload.get("symptom_durations")
        ),
        "safety_notes": safety_notes,
        "urgent_change": urgent_change,
        "red_flags": red_flags,
    }

    entries.append(entry)

    analysis = analyze_entry(
        entry,
        entries,
        model,
    )

    return jsonify(
        {
            **entry,
            **analysis,
        }
    )


@app.route("/api/recovery-summary")
def recovery_summary():
    data = enriched()

    return jsonify(
        {
            "summary": build_recovery_summary(
                data
            )
        }
    )


@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "RecoverPath AI",
            "entries_in_memory": len(entries),
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
