# RecoverPath AI

**A responsible-AI concussion recovery companion that helps people track symptoms, understand recovery patterns, plan daily activity, and prepare clearer information for conversations with healthcare professionals.**

Built for **Hack for Humanity Summer 2026**.

## Live Demo

https://recoverpathai.onrender.com

> **Important:** RecoverPath AI is a prototype and is not a medical device. It does not diagnose concussion, determine whether someone is medically safe, or replace professional medical care.

---

## The Problem

Concussion recovery can be difficult to understand day by day.

Symptoms such as headaches, dizziness, poor concentration, reduced screen tolerance, sleep problems, and difficulty returning to normal activity can change over time. A person may remember that they felt "better" or "worse," but it can be difficult to identify the actual pattern or communicate it clearly during a clinical visit.

RecoverPath AI was built to turn those daily observations into structured, understandable recovery information while deliberately avoiding the dangerous role of pretending to be a doctor.

The goal is not:

> "AI, tell me whether I am medically okay."

The goal is:

> "Help me organize what I am experiencing, recognize patterns in the information I recorded, and communicate those observations more clearly."

---

## What RecoverPath AI Does

RecoverPath AI combines a structured symptom diary, machine-learning pattern analysis, deterministic safety rules, recovery visualization, and explainable recommendations.

A user records information such as:

- Headache severity
- Dizziness
- Sleep quality
- Screen tolerance
- Concentration difficulty
- Activity tolerance
- Other recovery indicators

The application processes those observations and produces several useful outputs.

### 1. Daily Symptom Diary

Instead of relying on memory, users can record recovery indicators consistently on a 0–10 scale.

The interface explains the direction of each scale so that symptom severity and positive recovery indicators are interpreted correctly.

---

### 2. AI Recovery Pattern Classification

RecoverPath AI uses a **Random Forest machine-learning model** to analyze the combination of recovery indicators.

Rather than attempting to diagnose a medical condition, the model is constrained to identifying recovery-pattern categories from the information supplied by the user.

For example, the system can identify whether the recorded pattern appears to be:

- improving,
- relatively stable,
- or showing signs of deterioration.

This distinction is fundamental to the responsible-AI design.

**The ML model analyzes patterns. It does not make medical diagnoses.**

---

### 3. Recovery Timeline

A single day's score often tells very little.

RecoverPath AI therefore presents recovery information over time so users can see how their recorded symptoms and tolerance change across multiple check-ins.

The timeline helps make gradual trends visible instead of forcing users to judge recovery from memory.

---

### 4. Daily Recovery Plan

The system converts the current recovery pattern into a practical daily plan.

Recommendations are intentionally conservative and framed as supportive planning rather than medical instructions.

The objective is to help users think about pacing, activity, rest, screen exposure, and questions they may want to discuss with a healthcare professional.

---

### 5. Pattern Insights

RecoverPath AI explains the important signals contributing to the current pattern instead of presenting an unexplained AI output.

This makes the system more transparent and gives users context for what changed in their recorded information.

---

### 6. Doctor Visit Summary

One of the most practical goals of RecoverPath AI is improving communication.

The application converts tracked information into a structured summary that can help a user explain:

- what symptoms they have been recording,
- how those symptoms changed,
- what activities became easier or harder,
- what recovery pattern was observed,
- and what questions may be worth discussing.

RecoverPath AI does not replace the clinician.

It helps the user arrive with better-organized information.

---

## Responsible AI Architecture

Healthcare-related AI requires a different design philosophy from ordinary recommendation systems.

RecoverPath AI therefore separates **machine-learning pattern analysis** from **safety-critical decisions**.

### AI Layer

The Random Forest model is used for recovery-pattern classification.

It is useful for finding relationships across several recovery indicators, but its prediction is never treated as proof that a person is medically safe.

### Deterministic Safety Layer

Potential emergency warning conditions are handled separately from the ML prediction.

This means a favorable AI recovery classification cannot override a triggered safety warning.

Conceptually:

User check-in  
↓  
Safety rules evaluated  
↓  
Recovery features processed  
↓  
Random Forest pattern classification  
↓  
Pattern explanation  
↓  
Recovery plan + timeline + visit summary

Safety therefore does not depend exclusively on a probabilistic model.

---

## Why This Separation Matters

A machine-learning model can be wrong.

That becomes particularly important when software operates near healthcare decisions.

RecoverPath AI deliberately avoids statements such as:

- "You are safe."
- "Your concussion is healed."
- "You do not need medical attention."

Instead, the application distinguishes between what it actually knows and what it cannot know.

For example, the interface can report that:

> No urgent warning was triggered by this entry.

while explicitly clarifying that:

> This does not guarantee symptoms are medically safe.

That wording is intentional.

---

## Privacy-First Prototype

RecoverPath AI was designed as a privacy-conscious demonstration.

The prototype focuses on processing recovery information without requiring the user to create a public identity or social profile.

For a production healthcare deployment, additional requirements would be necessary, including appropriate authentication, encryption, data governance, clinical validation, regulatory review, and professional medical oversight.

This hackathon prototype does not claim those certifications.

---

## Technology

RecoverPath AI is built with:

- **Python**
- **Flask**
- **scikit-learn**
- **Random Forest machine learning**
- **NumPy / SciPy**
- **HTML/CSS**
- **Gunicorn**
- **Render** for cloud deployment
- **GitHub** for source control

---

## System Architecture

```text
                    RecoverPath AI
                          |
                   Daily Check-In
                          |
             +------------+------------+
             |                         |
       Safety Rules              Feature Processing
             |                         |
             |                  Random Forest Model
             |                         |
             +------------+------------+
                          |
                   Pattern Analysis
                          |
          +---------------+---------------+
          |               |               |
      Timeline       Recovery Plan    Pattern Insights
                          |
                   Visit Summary
