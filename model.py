import random
from collections import Counter

from sklearn.ensemble import RandomForestClassifier


# -------------------------------------------------------------------
# DETERMINISTIC SAFETY FLAGS
# -------------------------------------------------------------------
# These are intentionally kept separate from the ML model.
# RecoverPath does not use ML to decide whether urgent medical
# evaluation may be appropriate.
# -------------------------------------------------------------------

FLAGS = {
    "reported_significant_worsening": (
        "A sudden, severe, or significantly worsening change"
    ),
    "worsening_headache": (
        "A headache getting much worse"
    ),
    "repeated_vomiting": (
        "Repeated vomiting"
    ),
    "seizure": (
        "A seizure"
    ),
    "weakness": (
        "New weakness or numbness"
    ),
    "confusion": (
        "Increasing confusion"
    ),
    "hard_to_wake": (
        "Difficulty waking"
    ),
    "slurred_speech": (
        "Slurred speech"
    ),
    "vision_loss": (
        "Major new vision change"
    ),
}


# -------------------------------------------------------------------
# POSSIBLE TRIGGER TERMS
# -------------------------------------------------------------------
# These are simple keyword matches from user-written notes.
# They are not diagnoses and do not prove causation.
# -------------------------------------------------------------------

TRIGGERS = {
    "screen exposure": [
        "screen",
        "computer",
        "laptop",
        "phone",
        "gaming",
        "video",
        "tv",
        "monitor",
    ],
    "poor sleep": [
        "poor sleep",
        "bad sleep",
        "didn't sleep",
        "little sleep",
        "late night",
        "tired",
    ],
    "physical exertion": [
        "exercise",
        "running",
        "gym",
        "workout",
        "walking",
        "physical activity",
    ],
    "cognitive load": [
        "study",
        "studying",
        "work",
        "reading",
        "exam",
        "school",
        "concentration",
    ],
    "bright light": [
        "bright light",
        "sunlight",
        "lights",
        "brightness",
    ],
    "noise": [
        "noise",
        "loud",
        "music",
        "crowd",
    ],
    "stress": [
        "stress",
        "stressed",
        "anxiety",
        "anxious",
        "overwhelmed",
    ],
}


# -------------------------------------------------------------------
# ML MODEL
# -------------------------------------------------------------------

class RecoveryPatternModel:
    """
    Demonstration Random Forest model.

    The model uses six defined core recovery indicators:

    - headache severity
    - dizziness
    - sleep quality
    - screen tolerance
    - concentration difficulty
    - activity tolerance

    It also receives the previous calculated symptom burden.

    Training data is synthetic demonstration data. The classifier is
    intended to demonstrate recovery-pattern recognition, not diagnosis
    or medical-outcome prediction.
    """

    def __init__(self):
        random_generator = random.Random(42)

        features = []
        labels = []

        for _ in range(1200):
            values = [
                random_generator.randint(0, 10)
                for _ in range(6)
            ]

            previous_burden = random_generator.uniform(
                2,
                8,
            )

            current_burden = (
                values[0]
                + values[1]
                + values[4]
                + (10 - values[2])
                + (10 - values[3])
                + (10 - values[5])
            ) / 6

            delta = (
                current_burden
                - previous_burden
            )

            if delta < -0.8:
                label = "improving"

            elif delta > 0.8:
                label = "possible_setback"

            else:
                label = "stable"

            features.append(
                values
                + [previous_burden]
            )

            labels.append(label)

        self.clf = RandomForestClassifier(
            n_estimators=180,
            random_state=42,
            max_depth=6,
            min_samples_leaf=3,
        ).fit(
            features,
            labels,
        )

    def burden(self, entry):
        """
        Calculate normalized symptom burden.

        For headache, dizziness, and concentration difficulty,
        higher values mean greater burden.

        For sleep, screen tolerance, and activity tolerance,
        higher values mean better function, so their contribution
        to burden is inverted.
        """

        return round(
            (
                entry["headache"]
                + entry["dizziness"]
                + entry["concentration"]
                + (10 - entry["sleep"])
                + (10 - entry["screen_tolerance"])
                + (10 - entry["activity"])
            )
            / 6,
            2,
        )

    def predict(
        self,
        entry,
        history,
    ):
        current = self.burden(entry)

        previous = (
            self.burden(history[-2])
            if len(history) > 1
            else current
        )

        model_input = [[
            entry["headache"],
            entry["dizziness"],
            entry["sleep"],
            entry["screen_tolerance"],
            entry["concentration"],
            entry["activity"],
            previous,
        ]]

        probabilities = self.clf.predict_proba(
            model_input
        )[0]

        label = self.clf.predict(
            model_input
        )[0]

        confidence = round(
            float(max(probabilities)),
            2,
        )

        return (
            label,
            confidence,
            current,
            previous,
        )


# -------------------------------------------------------------------
# TRIGGER DETECTION
# -------------------------------------------------------------------

def detect_triggers(history):
    """
    Detect repeated trigger words in recent user notes.

    Keyword detection identifies possible associations only.
    It does not establish that a trigger caused a symptom.
    """

    found = Counter()

    for entry in history[-7:]:
        text = str(
            entry.get(
                "notes",
                "",
            )
        ).lower()

        for trigger, words in TRIGGERS.items():
            if any(
                word in text
                for word in words
            ):
                found[trigger] += 1

    return [
        {
            "name": name,
            "mentions": count,
        }
        for name, count
        in found.most_common(3)
    ]


# -------------------------------------------------------------------
# CORE SYMPTOM INSIGHTS
# -------------------------------------------------------------------

def symptom_insights(
    entry,
    history,
):
    """
    Compare the six defined core indicators.

    Custom symptoms are deliberately not mixed into the trained model.
    They remain additional tracking context in the application.
    """

    fields = {
        "headache": entry["headache"],
        "dizziness": entry["dizziness"],
        "concentration": entry["concentration"],
        "sleep": 10 - entry["sleep"],
        "screen tolerance": (
            10
            - entry["screen_tolerance"]
        ),
        "activity tolerance": (
            10
            - entry["activity"]
        ),
    }

    concern = max(
        fields,
        key=fields.get,
    )

    result = {
        "needs_attention": concern,
        "needs_attention_score": round(
            fields[concern],
            1,
        ),
        "most_improved": None,
        "most_worsened": None,
        "changes": {},
    }

    if len(history) <= 1:
        return result

    old = history[-2]

    # Positive = improvement.
    # Negative = worsening.
    changes = {
        "headache": (
            old["headache"]
            - entry["headache"]
        ),
        "dizziness": (
            old["dizziness"]
            - entry["dizziness"]
        ),
        "concentration": (
            old["concentration"]
            - entry["concentration"]
        ),
        "sleep": (
            entry["sleep"]
            - old["sleep"]
        ),
        "screen tolerance": (
            entry["screen_tolerance"]
            - old["screen_tolerance"]
        ),
        "activity tolerance": (
            entry["activity"]
            - old["activity"]
        ),
    }

    result["changes"] = changes

    best = max(
        changes,
        key=changes.get,
    )

    worst = min(
        changes,
        key=changes.get,
    )

    if changes[best] > 0:
        result["most_improved"] = best

    if changes[worst] < 0:
        result["most_worsened"] = worst

    return result


# -------------------------------------------------------------------
# RECOVERY INTELLIGENCE
# -------------------------------------------------------------------

def calculate_recovery_intelligence(
    entry,
    history,
    model,
):
    """
    Generate descriptive recovery metrics from recent check-ins.

    These scores describe recorded patterns only. They do not represent
    clinical recovery probability or medical prognosis.
    """

    burdens = [
        model.burden(item)
        for item in history[-7:]
    ]

    if not burdens:
        burdens = [
            model.burden(entry)
        ]

    current = model.burden(entry)

    if len(burdens) >= 2:
        change = round(
            burdens[-1]
            - burdens[0],
            2,
        )
    else:
        change = 0

    consistency = 100

    if len(burdens) >= 3:
        swings = [
            abs(
                burdens[index]
                - burdens[index - 1]
            )
            for index
            in range(
                1,
                len(burdens),
            )
        ]

        average_swing = (
            sum(swings)
            / len(swings)
        )

        consistency = max(
            0,
            round(
                100
                - average_swing * 12
            ),
        )

    # This is a descriptive normalized score derived from burden.
    # It is NOT a probability of recovery.
    recovery_score = round(
        max(
            0,
            min(
                100,
                (10 - current) * 10,
            ),
        )
    )

    return {
        "recovery_score": recovery_score,
        "seven_day_change": change,
        "consistency": consistency,
        "entries_analyzed": min(
            len(history),
            7,
        ),
        "score_type": (
            "descriptive_normalized_burden_score"
        ),
    }


# -------------------------------------------------------------------
# SAFETY
# -------------------------------------------------------------------

def evaluate_safety(entry):
    """
    Evaluate explicitly reported safety information.

    This function is deterministic. No ML output is used here.
    """

    reported_flags = entry.get(
        "red_flags",
        [],
    )

    if not isinstance(
        reported_flags,
        list,
    ):
        reported_flags = []

    matched_flags = [
        FLAGS[flag]
        for flag in reported_flags
        if flag in FLAGS
    ]

    # The new frontend also sends urgent_change directly.
    # Treat it as an explicit user-reported significant worsening.
    urgent_change = bool(
        entry.get(
            "urgent_change",
            False,
        )
    )

    if (
        urgent_change
        and FLAGS[
            "reported_significant_worsening"
        ]
        not in matched_flags
    ):
        matched_flags.append(
            FLAGS[
                "reported_significant_worsening"
            ]
        )

    # Additional deterministic threshold safeguard.
    severe_score_combination = (
        entry["headache"] >= 9
        and entry["dizziness"] >= 8
    )

    urgent = bool(
        matched_flags
    ) or severe_score_combination

    if severe_score_combination:
        threshold_message = (
            "Very high headache and dizziness scores "
            "were reported together."
        )
    else:
        threshold_message = ""

    return {
        "urgent": urgent,
        "title": (
            "Urgent safety warning"
            if urgent
            else ""
        ),
        "message": (
            "Concerning or significantly worsening "
            "symptoms were reported. Seek prompt medical "
            "evaluation. For severe, rapidly worsening, "
            "or emergency symptoms, contact local emergency "
            "services."
            if urgent
            else ""
        ),
        "matched_flags": matched_flags,
        "threshold_message": threshold_message,
        "decision_source": (
            "deterministic_rule_based_safety_system"
        ),
        "ml_used_for_safety": False,
    }


# -------------------------------------------------------------------
# GUIDANCE
# -------------------------------------------------------------------

def build_guidance(
    entry,
    label,
):
    """
    Produce conservative, non-diagnostic follow-up suggestions.
    """

    tips = []

    if entry["screen_tolerance"] <= 4:
        tips.append(
            "Consider pacing screen use with shorter "
            "sessions and symptom-guided breaks."
        )

    if entry["sleep"] <= 4:
        tips.append(
            "Consider protecting a consistent sleep "
            "routine and reducing late-night stimulation."
        )

    if entry["concentration"] >= 7:
        tips.append(
            "Consider reducing cognitive load by "
            "breaking demanding tasks into shorter blocks."
        )

    if entry["activity"] <= 4:
        tips.append(
            "Follow activity guidance from your clinician. "
            "If medically cleared and tolerated, avoid "
            "pushing through significant symptom worsening."
        )

    if label == "possible_setback":
        tips.insert(
            0,
            (
                "The recorded pattern suggests a possible "
                "setback or symptom flare. Consider reducing "
                "demanding activity and discussing persistent "
                "or worsening symptoms with a clinician."
            ),
        )

    if not tips:
        tips.append(
            "Continue recording check-ins consistently "
            "so changes are easier to identify over time."
        )

    return tips[:4]


# -------------------------------------------------------------------
# ENTRY ANALYSIS
# -------------------------------------------------------------------

def analyze_entry(
    entry,
    history,
    model,
):
    """
    Analyze one recovery check-in.

    ML:
        recovery-pattern classification

    Deterministic logic:
        urgent safety evaluation

    Descriptive calculations:
        burden, symptom changes, consistency, trigger keywords
    """

    (
        label,
        confidence,
        burden,
        previous,
    ) = model.predict(
        entry,
        history,
    )

    safety = evaluate_safety(
        entry
    )

    triggers = detect_triggers(
        history
    )

    insights = symptom_insights(
        entry,
        history,
    )

    intelligence = (
        calculate_recovery_intelligence(
            entry,
            history,
            model,
        )
    )

    guidance = build_guidance(
        entry,
        label,
    )

    headline = {
        "improving": (
            "Your recent recorded recovery pattern "
            "is trending better."
        ),
        "stable": (
            "Your recent recorded recovery pattern "
            "looks relatively stable."
        ),
        "possible_setback": (
            "Your recent recorded pattern may reflect "
            "a setback or symptom flare."
        ),
    }[label]

    return {
        "pattern": label,
        "confidence": confidence,
        "burden_score": burden,
        "previous_burden": previous,
        "headline": headline,
        "guidance": guidance,
        "safety": safety,
        "triggers": triggers,
        "symptom_insights": insights,
        "recovery_intelligence": intelligence,
        "model_information": {
            "type": "Random Forest classifier",
            "training_data": (
                "synthetic demonstration data"
            ),
            "purpose": (
                "recovery-pattern classification"
            ),
            "model_inputs": [
                "headache",
                "dizziness",
                "sleep quality",
                "screen tolerance",
                "concentration difficulty",
                "activity tolerance",
                "previous calculated symptom burden",
            ],
            "custom_symptoms_used_by_model": False,
            "used_for_diagnosis": False,
            "used_for_emergency_decisions": False,
        },
    }
