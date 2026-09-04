from flask import Flask,render_template,request,jsonify
from model import RecoveryPatternModel,analyze_entry
app=Flask(__name__); model=RecoveryPatternModel()
entries=[
{"day":1,"headache":7,"dizziness":6,"sleep":4,"screen_tolerance":3,"concentration":7,"activity":2,"notes":"Resting most of the day."},
{"day":2,"headache":6,"dizziness":5,"sleep":5,"screen_tolerance":4,"concentration":6,"activity":3,"notes":"Slight improvement."},
{"day":3,"headache":5,"dizziness":4,"sleep":6,"screen_tolerance":5,"concentration":5,"activity":4,"notes":"Could tolerate a short walk."}]
def enriched():
 return [{**e,**analyze_entry(e,entries[:i+1],model)} for i,e in enumerate(entries)]
def plan(e):
 if not e:return []
 p=[]
 if e["screen_tolerance"]<=4:p.append(["Pace screen time","Use shorter screen sessions and symptom-guided breaks."])
 if e["concentration"]>=6:p.append(["Reduce cognitive load","Use shorter work/study blocks and avoid multitasking."])
 if e["sleep"]<=5:p.append(["Protect sleep","Keep a consistent bedtime and reduce late-night stimulation."])
 if e["activity"]<=4:p.append(["Gentle activity","If medically cleared and tolerated, consider light activity without pushing through symptoms."])
 if e["headache"]>=7 or e["dizziness"]>=7:p.append(["Lower today's load","Scale back demanding activities and contact a clinician if symptoms worsen."])
 return p[:4] or [["Maintain a steady pace","Continue tracking and avoid sudden large increases in activity."]]
def insights(data):
 if len(data)<2:return ["Add another check-in to begin comparing patterns."]
 a,b=data[0],data[-1]; d=round(b["burden_score"]-a["burden_score"],1)
 out=[f"Overall symptom burden changed from {a['burden_score']}/10 on Day {a['day']} to {b['burden_score']}/10 on Day {b['day']}."]
 best=max(data,key=lambda x:x["screen_tolerance"])
 out.append(f"Best recorded screen tolerance is {best['screen_tolerance']}/10 on Day {best['day']}.")
 high=max(data,key=lambda x:x["headache"])
 if high["headache"]>=7:out.append(f"Highest recorded headache is {high['headache']}/10 on Day {high['day']}; reviewing notes from high-symptom days may help identify triggers.")
 return out
def summary(data):
 if not data:return "No entries recorded yet."
 a,b=data[0],data[-1]; urgent=[str(x["day"]) for x in data if x["safety"]["urgent"]]
 s=[f"RecoverPath AI clinician summary — {len(data)} recorded day(s)",
 f"Current non-diagnostic pattern: {b['pattern'].replace('_',' ')}.",
 f"Symptom burden: Day {a['day']} {a['burden_score']}/10 → Day {b['day']} {b['burden_score']}/10.",
 f"Latest: headache {b['headache']}/10; dizziness {b['dizziness']}/10; sleep {b['sleep']}/10; screen tolerance {b['screen_tolerance']}/10; concentration difficulty {b['concentration']}/10; activity tolerance {b['activity']}/10."]
 if urgent:s.append("Urgent safety warning triggered on day(s): "+", ".join(urgent)+".")
 notes=[f"Day {x['day']}: {x.get('notes','')}" for x in data if x.get("notes")]
 if notes:s.append("Recent notes: "+" | ".join(notes[-4:]))
 s.append("Generated from self-reported entries; not a diagnosis or clinical assessment.")
 return "\n".join(s)
@app.route("/")
def home():return render_template("index.html")
@app.route("/api/status")
def status():
 d=enriched(); latest=d[-1] if d else None
 return jsonify(entries=d,latest=latest,daily_plan=plan(latest),insights=insights(d),clinician_summary=summary(d))
@app.route("/api/entry",methods=["POST"])
def add():
 x=request.get_json(force=True)
 e={"day":len(entries)+1,**{k:int(x[k]) for k in ["headache","dizziness","sleep","screen_tolerance","concentration","activity"]},"notes":str(x.get("notes",""))[:500],"red_flags":x.get("red_flags",[])}
 entries.append(e);return jsonify({**e,**analyze_entry(e,entries,model)})
if __name__=="__main__":app.run(host="127.0.0.1",port=5000,debug=True)
