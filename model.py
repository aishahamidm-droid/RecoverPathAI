import random
import re
from collections import Counter
from sklearn.ensemble import RandomForestClassifier

FLAGS = {
    "worsening_headache": "A headache getting much worse",
    "repeated_vomiting": "Repeated vomiting",
    "seizure": "A seizure",
    "weakness": "New weakness or numbness",
    "confusion": "Increasing confusion",
    "hard_to_wake": "Difficulty waking",
    "slurred_speech": "Slurred speech",
    "vision_loss": "Major new vision change",
}

TRIGGERS = {
    "screen exposure": [
        "screen", "computer", "laptop", "phone", "gaming",
        "video", "tv", "monitor"
    ],
    "poor sleep": [
        "poor sleep", "bad sleep", "didn't sleep",
        "little sleep", "late night", "tired"
    ],
    "physical exertion": [
        "exercise", "running", "gym", "workout",
        "walking", "physical activity"
    ],
    "cognitive load": [
        "study", "studying", "work", "reading",
        "exam", "school", "concentration"
    ],
    "bright light": [
        "bright light", "sunlight", "lights", "brightness"
    ],
    "noise": [
        "noise", "loud", "music", "crowd"
    ],
}


class RecoveryPatternModel:
    def __init__(self):
        r = random.Random(42)
        X, y = [], []

        for _ in range(1200):
            v = [r.randint(0, 10) for _ in range(6)]
            prev = r.uniform(2, 8)

            cur = (
                v[0] + v[1] + v[4]
                + 10 - v[2]
                + 10 - v[3]
                + 10 - v[5]
            ) / 6

            delta = cur - prev

            if delta < -0.8:
                label = "improving"
            elif delta > 0.8:
                label = "possible_setback"
            else:
                label = "stable"

            X.append(v + [prev])
            y.append(label)

        self.clf = RandomForestClassifier(
            n_estimators=180,
            random_state=42,
            max_depth=6,
            min_samples_leaf=3,
        ).fit(X, y)

    def burden(self, e):
        return round(
            (
                e["headache"]
                + e["dizziness"]
                + e["concentration"]
                + (10 - e["sleep"])
                + (10 - e["screen_tolerance"])
                + (10 - e["activity"])
            ) / 6,
            2,
        )

    def predict(self, e, history):
        current = self.burden(e)

        previous = (
            self.burden(history[-2])
            if len(history) > 1
            else current
        )

        x = [[
            e["headache"],
            e["dizziness"],
            e["sleep"],
            e["screen_tolerance"],
            e["concentration"],
            e["activity"],
            previous,
        ]]

        probabilities = self.clf.predict_proba(x)[0]
        label = self.clf.predict(x)[0]

        return (
            label,
            round(float(max(probabilities)), 2),
            current,
            previous,
        )


def detect_triggers(history):
    found = Counter()

    for entry in history[-7:]:
        text = str(entry.get("notes", "")).lower()

        for trigger, words in TRIGGERS.items():
            if any(word in text for word in words):
                found[trigger] += 1

    return [
        {"name": name, "mentions": count}
        for name, count in found.most_common(3)
    ]


def symptom_insights(entry, history):
    fields = {
        "headache": entry["headache"],
        "dizziness": entry["dizziness"],
        "concentration": entry["concentration"],
        "sleep": 10 - entry["sleep"],
        "screen tolerance": 10 - entry["screen_tolerance"],
        "activity tolerance": 10 - entry["activity"],
    }

    concern = max(fields, key=fields.get)

    result = {
        "needs_attention": concern,
        "needs_attention_score": round(fields[concern], 1),
        "most_improved": None,
    }

    if len(history) > 1:
        old = history[-2]

        improvements = {
            "headache": old["headache"] - entry["headache"],
            "dizziness": old["dizziness"] - entry["dizziness"],
            "concentration": (
                old["concentration"] - entry["concentration"]
            ),
            "sleep": entry["sleep"] - old["sleep"],
            "screen tolerance": (
                entry["screen_tolerance"]
                - old["screen_tolerance"]
            ),
            "activity tolerance": (
                entry["activity"] - old["activity"]
            ),
        }

        best = max(improvements, key=improvements.get)

        if improvements[best] > 0:
            result["most_improved"] = best

    return result


def calculate_recovery_intelligence(entry, history, model):
    burdens = [model.burden(x) for x in history[-7:]]

    if not burdens:
        burdens = [model.burden(entry)]

    current = model.burden(entry)

    if len(burdens) >= 2:
        change = round(burdens[-1] - burdens[0], 2)
    else:
        change = 0

    consistency = 100

    if len(burdens) >= 3:
        swings = [
            abs(burdens[i] - burdens[i - 1])
            for i in range(1, len(burdens))
        ]
        consistency = max(
            0,
            round(100 - (sum(swings) / len(swings)) * 12)
        )

    recovery_score = round(max(0, min(100, (10 - current) * 10)))

    return {
        "recovery_score": recovery_score,
        "seven_day_change": change,
        "consistency": consistency,
        "entries_analyzed": min(len(history), 7),
    }


def build_clinician_summary(entry, analysis):
    pattern = analysis["pattern"].replace("_", " ")

    summary = (
        f"Current symptom burden: "
        f"{analysis['burden_score']}/10. "
        f"Recovery pattern: {pattern}. "
    )

    insights = analysis["symptom_insights"]

    if insights["needs_attention"]:
        summary += (
            f"Highest current burden area: "
            f"{insights['needs_attention']}. "
        )

    if analysis["triggers"]:
        names = ", ".join(
            item["name"] for item in analysis["triggers"]
        )
        summary += f"Possible reported triggers: {names}. "

    if analysis["safety"]["urgent"]:
        summary += (
            "Urgent warning signs were reported and medical "
            "evaluation was advised."
        )
    else:
        summary += "No emergency warning sign was recorded in this entry."

    return summary


def analyze_entry(e, h, m):
    label, conf, burden, prev = m.predict(e, h)

    flags = [
        FLAGS[x]
        for x in e.get("red_flags", [])
        if x in FLAGS
    ]

    # Safety rules are deliberately deterministic.
    # ML is NOT used to decide whether emergency care is needed.
    urgent = bool(flags) or (
        e["headache"] >= 9 and e["dizziness"] >= 8
    )

    safety = {
        "urgent": urgent,
        "title": "Urgent safety warning" if urgent else "",
        "message": (
            "Concerning warning signs were recorded. "
            "Seek urgent medical evaluation now; contact local "
            "emergency services for severe or rapidly worsening symptoms."
            if urgent
            else ""
        ),
        "matched_flags": flags,
        "decision_source": "rule_based_safety_system",
    }

    tips = []

    if e["screen_tolerance"] <= 4:
        tips.append(
            "Pace screen time with shorter sessions and "
            "symptom-guided breaks."
        )

    if e["sleep"] <= 4:
        tips.append(
            "Protect sleep with a consistent routine and "
            "reduced late-night stimulation."
        )

    if e["concentration"] >= 7:
        tips.append(
            "Reduce cognitive load by breaking demanding "
            "tasks into shorter blocks."
        )

    if e["activity"] <= 4:
        tips.append(
            "If medically cleared and tolerated, consider gentle "
            "activity without pushing through worsening symptoms."
        )

    if label == "possible_setback":
        tips.insert(
            0,
            "Your recent pattern suggests a possible setback. "
            "Consider reducing load and discussing persistent "
            "or worsening symptoms with a clinician."
        )

    triggers = detect_triggers(h)
    insights = symptom_insights(e, h)
    intelligence = calculate_recovery_intelligence(e, h, m)

    result = {
        "pattern": label,
        "confidence": conf,
        "burden_score": burden,
        "previous_burden": prev,
        "headline": {
            "improving":
                "Your recent recovery pattern is trending better.",
            "stable":
                "Your recent recovery pattern looks relatively stable.",
            "possible_setback":
                "Your recent pattern may reflect a setback "
                "or symptom flare.",
        }[label],
        "guidance": tips[:4] or [
            "Continue tracking consistently so changes "
            "are easier to identify."
        ],
        "safety": safety,
        "triggers": triggers,
        "symptom_insights": insights,
        "recovery_intelligence": intelligence,
    }

    result["clinician_summary"] = build_clinician_summary(e, result)

    return result