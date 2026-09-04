import random
from sklearn.ensemble import RandomForestClassifier
FLAGS={"worsening_headache":"A headache getting much worse","repeated_vomiting":"Repeated vomiting","seizure":"A seizure","weakness":"New weakness or numbness","confusion":"Increasing confusion","hard_to_wake":"Difficulty waking","slurred_speech":"Slurred speech","vision_loss":"Major new vision change"}
class RecoveryPatternModel:
 def __init__(self):
  r=random.Random(42);X=[];y=[]
  for _ in range(900):
   v=[r.randint(0,10) for _ in range(6)];prev=r.uniform(2,8); cur=(v[0]+v[1]+v[4]+10-v[2]+10-v[3]+10-v[5])/6;delta=cur-prev
   X.append(v+[prev]);y.append("improving" if delta<-.8 else "possible_setback" if delta>.8 else "stable")
  self.clf=RandomForestClassifier(n_estimators=120,random_state=42,max_depth=5).fit(X,y)
 def burden(self,e):return round((e["headache"]+e["dizziness"]+e["concentration"]+10-e["sleep"]+10-e["screen_tolerance"]+10-e["activity"])/6,2)
 def predict(self,e,h):
  cur=self.burden(e);prev=self.burden(h[-2]) if len(h)>1 else cur;x=[[e["headache"],e["dizziness"],e["sleep"],e["screen_tolerance"],e["concentration"],e["activity"],prev]]
  return self.clf.predict(x)[0],round(float(max(self.clf.predict_proba(x)[0])),2),cur,prev
def analyze_entry(e,h,m):
 label,conf,b,prev=m.predict(e,h); flags=[FLAGS[x] for x in e.get("red_flags",[]) if x in FLAGS]
 urgent=bool(flags) or (e["headache"]>=9 and e["dizziness"]>=8)
 safety={"urgent":urgent,"title":"Urgent safety warning" if urgent else "","message":"Concerning warning signs were recorded. Seek urgent medical evaluation now; contact local emergency services for severe or rapidly worsening symptoms." if urgent else "","matched_flags":flags}
 tips=[]
 if e["screen_tolerance"]<=4:tips.append("Consider shorter screen sessions with regular breaks if screens worsen symptoms.")
 if e["sleep"]<=4:tips.append("Prioritize a consistent sleep routine.")
 if e["concentration"]>=7:tips.append("Break demanding tasks into shorter blocks.")
 if label=="possible_setback":tips.insert(0,"Reduce load temporarily and consider contacting a clinician if symptoms are worsening.")
 return {"pattern":label,"confidence":conf,"burden_score":b,"previous_burden":prev,"headline":{"improving":"Your recent pattern looks better than the previous entry.","stable":"Your recent pattern looks relatively stable.","possible_setback":"Your recent pattern may reflect a setback or symptom flare."}[label],"guidance":tips[:4] or ["Continue tracking consistently so changes are easier to spot."],"safety":safety}
