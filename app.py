from flask import Flask, render_template, request, jsonify
from model import RecoveryPatternModel, analyze_entry

app = Flask(__name__)
model = RecoveryPatternModel()

entries = [
    {
        "day": 1,
        "headache": 7,
        "dizziness": 6,
        "sleep": 4,
        "screen_tolerance": 3,
        "concentration": 7,
        "activity": 2,
        "notes": "Resting most of the day after significant screen exposure.",
    },
    {
        "day": 2,
        "headache": 6,
        "dizziness": 5,
        "sleep": 5,
        "screen_tolerance": 4,
        "concentration": 6,
        "activity": 3,
        "notes": "Slight improvement after reducing screen time.",
    },
    {
        "day": 3,
        "headache": 5,
        "dizziness": 4,
        "sleep": 6,
        "screen_tolerance": 5,
        "concentration": 5,
        "activity": 4,
        "notes": "Could tolerate a short walk and some reading.",
    },
]


def enriched():
    results = []

    for i, entry in enumerate(entries):
        history = entries[: i + 1]
        analysis = analyze_entry(entry, history, model)
        results.append({**entry, **analysis})

    return results


def build_daily_plan(latest):
    if not latest:
        return []

    plan = []

    if latest["pattern"] == "possible_setback":
        plan.append([
            "Recovery reset",
            "Recent changes suggest a possible setback. "
            "Reduce demanding activity and monitor symptoms."
        ])

    if latest["screen_tolerance"] <= 4:
        plan.append([
            "Pace screen time",
            "Use shorter screen sessions with symptom-guided breaks."
        ])

    if latest["concentration"] >= 6:
        plan.append([
            "Reduce cognitive load",
            "Use shorter work or study blocks and avoid multitasking."
        ])

    if latest["sleep"] <= 5:
        plan.append([
            "Protect sleep",
            "Keep a consistent bedtime and reduce late-night stimulation."
        ])

    if latest["activity"] <= 4:
        plan.append([
            "Gentle activity",
            "If medically cleared and tolerated, consider light activity "
            "without pushing through worsening symptoms."
        ])

    if latest["headache"] >= 7 or latest["dizziness"] >= 7:
        plan.append([
            "Lower today's load",
            "Scale back demanding activities and contact a clinician "
            "if symptoms continue to worsen."
        ])

    return plan[:4] or [[
        "Maintain a steady pace",
        "Continue tracking and avoid sudden large increases in activity."
    ]]


def build_insights(data):
    if not data:
        return []

    latest = data[-1]
    intelligence = latest["recovery_intelligence"]
    symptoms = latest["symptom_insights"]

    output = []

    output.append(
        f"Recovery Intelligence Score: "
        f"{intelligence['recovery_score']}/100."
    )

    if len(data) >= 2:
        change = round(
            data[-1]["burden_score"] - data[0]["burden_score"], 2
        )

        if change < 0:
            output.append(
                f"Overall symptom burden improved by "
                f"{abs(change)} points since Day {data[0]['day']}."
            )
        elif change > 0:
            output.append(
                f"Overall symptom burden increased by "
                f"{change} points since Day {data[0]['day']}."
            )
        else:
            output.append(
                "Overall symptom burden has remained stable."
            )

    if symptoms.get("most_improved"):
        output.append(
            f"Most improved area since the previous entry: "
            f"{symptoms['most_improved']}."
        )

    output.append(
        f"Area currently needing the most attention: "
        f"{symptoms['needs_attention']}."
    )

    triggers = latest.get("triggers", [])

    if triggers:
        strongest = triggers[0]
        output.append(
            f"Most frequently reported possible trigger: "
            f"{strongest['name']} "
            f"({strongest['mentions']} recent mention(s))."
        )
    else:
        output.append(
            "No repeated trigger has been identified from recent notes yet."
        )

    output.append(
        f"Recovery consistency score: "
        f"{intelligence['consistency']}/100."
    )

    return output


def build_clinician_summary(data):
    if not data:
        return "No entries recorded yet."

    latest = data[-1]
    first = data[0]

    lines = [
        "RECOVERPATH AI — RECOVERY SUMMARY",
        "",
        f"Entries analyzed: {len(data)}",
        (
            f"Current recovery pattern: "
            f"{latest['pattern'].replace('_', ' ')}"
        ),
        (
            f"Current symptom burden: "
            f"{latest['burden_score']}/10"
        ),
        (
            f"Recovery Intelligence Score: "
            f"{latest['recovery_intelligence']['recovery_score']}/100"
        ),
        (
            f"Burden change: {first['burden_score']}/10 "
            f"on Day {first['day']} → "
            f"{latest['burden_score']}/10 "
            f"on Day {latest['day']}"
        ),
        "",
        "LATEST SELF-REPORTED SYMPTOMS",
        f"Headache: {latest['headache']}/10",
        f"Dizziness: {latest['dizziness']}/10",
        f"Sleep quality: {latest['sleep']}/10",
        f"Screen tolerance: {latest['screen_tolerance']}/10",
        (
            f"Concentration difficulty: "
            f"{latest['concentration']}/10"
        ),
        f"Activity tolerance: {latest['activity']}/10",
    ]

    triggers = latest.get("triggers", [])

    if triggers:
        lines.extend([
            "",
            "POSSIBLE REPORTED TRIGGERS",
        ])

        for trigger in triggers:
            lines.append(
                f"- {trigger['name']}: "
                f"{trigger['mentions']} recent mention(s)"
            )

    urgent_days = [
        str(item["day"])
        for item in data
        if item["safety"]["urgent"]
    ]

    if urgent_days:
        lines.extend([
            "",
            "SAFETY",
            (
                "Urgent warning criteria were triggered on day(s): "
                + ", ".join(urgent_days)
            ),
        ])

    notes = [
        f"Day {item['day']}: {item.get('notes', '')}"
        for item in data
        if item.get("notes")
    ]

    if notes:
        lines.extend([
            "",
            "RECENT NOTES",
            *notes[-4:],
        ])

    lines.extend([
        "",
        "RESPONSIBLE AI NOTICE",
        (
            "Machine learning is used to identify recovery-pattern "
            "changes, not to diagnose concussion or determine emergencies."
        ),
        (
            "Urgent safety warnings are generated by explicit "
            "rule-based criteria."
        ),
        (
            "This summary is based on self-reported information "
            "and is not a diagnosis or clinical assessment."
        ),
    ])

    return "\n".join(lines)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/status")
def status():
    data = enriched()
    latest = data[-1] if data else None

    return jsonify(
        entries=data,
        latest=latest,
        daily_plan=build_daily_plan(latest),
        insights=build_insights(data),
        clinician_summary=build_clinician_summary(data),
        responsible_ai={
            "ml_role": (
                "Random Forest classification identifies changes "
                "in self-reported recovery patterns."
            ),
            "safety_role": (
                "Emergency warning signs are evaluated using "
                "deterministic rules rather than ML predictions."
            ),
            "limitations": (
                "RecoverPath AI does not diagnose concussion, "
                "predict medical outcomes, or replace professional care."
            ),
        },
    )


@app.route("/api/entry", methods=["POST"])
def add():
    payload = request.get_json(force=True)

    entry = {
        "day": len(entries) + 1,
        **{
            key: int(payload[key])
            for key in [
                "headache",
                "dizziness",
                "sleep",
                "screen_tolerance",
                "concentration",
                "activity",
            ]
        },
        "notes": str(payload.get("notes", ""))[:500],
        "red_flags": payload.get("red_flags", []),
    }

    entries.append(entry)

    analysis = analyze_entry(entry, entries, model)

    return jsonify({
        **entry,
        **analysis,
    })


@app.route("/api/clinician-summary")
def clinician_summary():
    data = enriched()

    return jsonify({
        "summary": build_clinician_summary(data)
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )