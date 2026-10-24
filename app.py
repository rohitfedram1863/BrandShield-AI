import os,re,json,sqlite3
from datetime import datetime
from flask import Flask,request,redirect,url_for,render_template_string,flash,jsonify
app=Flask(__name__); app.secret_key=os.environ.get("BRANDSHIELD_SECRET_KEY","change-this-before-deployment")
DB=os.environ.get("BRANDSHIELD_DB",os.path.join(os.path.dirname(__file__),"brandshield.db"))
DEFAULT=[
("prohibited_term","Avoid the phrase guaranteed results.","guaranteed results","high"),
("prohibited_term","Avoid unsupported ranking claims such as No. 1 or best in India.","No. 1","high"),
("required_phrase","Use approved availability wording where relevant.","available on selected plans","medium"),
("tone","Prefer specific, respectful language over hype or pressure.","tone","medium"),
("disclaimer","Promotional claims need approved supporting evidence.","evidence","high")]
FACTS=[("Product availability","The product is available on selected plans."),
("Support hours","Customer support is available Monday to Friday, 9 AM to 5 PM."),
("Free access","No approved fact confirms that the product is free for everyone.")]
def conn(): 
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 c=conn()
 c.execute("CREATE TABLE IF NOT EXISTS rules(id INTEGER PRIMARY KEY,category TEXT,rule_text TEXT,trigger_text TEXT,severity TEXT,active INTEGER DEFAULT 1)")
 c.execute("CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY,title TEXT,fact_text TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,title TEXT,content TEXT,findings TEXT,status TEXT,created TEXT,updated TEXT,note TEXT DEFAULT '')")
 if c.execute("SELECT COUNT(*) n FROM rules").fetchone()["n"]==0:c.executemany("INSERT INTO rules(category,rule_text,trigger_text,severity) VALUES(?,?,?,?)",DEFAULT)
 if c.execute("SELECT COUNT(*) n FROM facts").fetchone()["n"]==0:c.executemany("INSERT INTO facts(title,fact_text) VALUES(?,?)",FACTS)
 c.commit();c.close()
def rows(table): 
 c=conn(); r=[dict(x) for x in c.execute(f"SELECT * FROM {table}"+(" WHERE active=1" if table=="rules" else "")+" ORDER BY id DESC")];c.close();return r
def analyse(text):
 low=text.lower(); findings=[]; rules=rows("rules"); facts=rows("facts"); seen=set()
 def add(cat,sev,match,why,evidence,suggest,status="Flagged"):
  key=(cat,match.lower(),why)
  if key not in seen:
   seen.add(key);findings.append(dict(category=cat,severity=sev,matched_text=match,explanation=why,evidence=evidence,suggestion=suggest,status=status))
 for r in rules:
  tr=(r["trigger_text"] or "").strip()
  if r["category"]=="prohibited_term" and tr and tr.lower() in low:
   add("Terminology / claim",r["severity"],tr,"This phrase matches a configured brand rule.",r["rule_text"],"Replace it with a specific, verifiable statement supported by an approved source.")
  elif r["category"]=="required_phrase" and tr and tr.lower() not in low:
   add("Required wording",r["severity"],"(required phrase missing)","The configured approved phrase does not appear in this draft.",r["rule_text"],"If relevant, include the approved wording or ask the brand owner whether it applies.")
  elif r["category"]=="disclaimer":
   patterns=[(r"\b(no\.?\s*1|number one|best in india|india's best|world's best)\b","ranking / superlative claim"),
   (r"\b(100%\s*(safe|effective|guaranteed)|guaranteed results|risk[- ]free)\b","absolute or guarantee claim"),
   (r"\b(free for everyone|always free|zero cost for all)\b","pricing / access claim")]
   for pat,label in patterns:
    m=re.search(pat,text,re.I)
    if m:add("Unsupported claim","high",m.group(0),f"This looks like a {label}. The configured knowledge base does not prove it.","No supporting source was found in the demo knowledge base. This does not prove the claim false.","Remove it, qualify it using an approved fact, or request human verification.","Needs verification")
  elif r["category"]=="tone":
   for pat,why in [(r"\b(mind[- ]blowing|insane results|unbelievable|act now or regret|guaranteed success)\b","Wording may feel exaggerated or pressuring.")]:
    m=re.search(pat,text,re.I)
    if m:add("Tone",r["severity"],m.group(0),why,r["rule_text"],"Use a calm, specific description without pressure.")
 if re.search(r"\bfree for everyone\b|\balways free\b",text,re.I):
  f=next((x for x in facts if "free access" in x["title"].lower()),None)
  add("Fact verification","high","free for everyone","No approved fact confirms universal free access.",f["fact_text"] if f else "No approved fact available.","Use only pricing/access wording approved by the organisation.","Needs verification")
 if not findings:findings=[dict(category="Initial review",severity="low",matched_text="No configured rule triggered",explanation="No issue was detected by the current rules. This does not guarantee accuracy or compliance.",evidence=f"{len(rules)} configured rules checked.",suggestion="Continue human review and verify important claims.",status="No rule triggered")]
 return findings
def rewrite(text):
 for old,new in [("guaranteed results","results may vary depending on use"),("No. 1","designed to support your workflow"),("best in India","built to support your needs"),("free for everyone","available on selected plans"),("act now or regret","explore the available options"),("insane results","measurable results"),("mind-blowing","useful"),("unbelievable","notable"),("100% safe","designed with safety in mind"),("guaranteed success","support for your goals")]:
  text=re.sub(re.escape(old),new,text,flags=re.I)
 return text
def optional_ai(text,findings):
 key=os.environ.get("GEMINI_API_KEY")
 if not key:return None,"Optional Gemini review is not configured; deterministic checks are active."
 try:
  import requests
  prompt="Review tone and clarity only. Do not invent facts. Return JSON with tone_observation and suggested_rewrite. Draft:\n"+text[:5000]+"\nExisting findings:\n"+json.dumps(findings[:10])
  u="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
  r=requests.post(u,params={"key":key},json={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.2,"responseMimeType":"application/json"}},timeout=15);r.raise_for_status()
  result=json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"]);return result,"Optional Gemini review completed."
 except Exception:return None,"Optional AI request failed; deterministic findings remain available."
CSS="""*{box-sizing:border-box}body{margin:0;background:#f6f8fc;color:#243244;font:15px/1.55 system-ui,Segoe UI,sans-serif}a{color:inherit;text-decoration:none}.bar{padding:18px max(20px,calc((100% - 1080px)/2));background:#fff;border-bottom:1px solid #dce4ee;display:flex;justify-content:space-between;gap:18px;align-items:center}.brand{font-weight:900;color:#14263d;font-size:19px}.brand b{color:#2f6fed}.bar nav{display:flex;gap:18px;font-size:13px;color:#637187}.wrap{max-width:1080px;padding:0 22px;margin:auto}.hero{display:grid;grid-template-columns:1.2fr .8fr;gap:35px;padding:55px 0 35px;align-items:center}.eyebrow{font-size:10px;letter-spacing:1.6px;color:#18a999;font-weight:900}.hero h1{font-size:54px;line-height:1.05;letter-spacing:-2px;color:#14263d;margin:10px 0}.hero h1 span{color:#2f6fed}.muted,small{color:#637187}.panel,.card{background:#fff;border:1px solid #dce4ee;border-radius:15px;padding:21px;margin-bottom:14px}.panel{background:#14263d;color:#fff}.panel h3{color:#fff}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0 45px}.stats .card{margin:0}.stats strong{display:block;font-size:23px;color:#14263d}.section{padding:20px 0 35px;scroll-margin-top:20px}.section h2{color:#14263d;font-size:28px;margin:0}.sectionhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}label{display:block;font-size:12px;font-weight:800;margin:12px 0 6px}input,textarea,select{width:100%;padding:11px;border:1px solid #d4deea;border-radius:8px;background:#fbfcff;font:inherit;font-size:13px;color:#243244}textarea{resize:vertical}.btn{display:inline-block;border:0;border-radius:9px;padding:11px 15px;background:#2f6fed;color:white;font-weight:800;cursor:pointer;margin-top:12px}.btn.alt{background:#eaf0ff;color:#244eb0}.row{padding:12px 0;border-top:1px solid #edf0f5;display:flex;gap:10px;align-items:flex-start}.row div{flex:1}.tag{font-size:10px;text-transform:uppercase;font-weight:900;padding:4px 7px;border-radius:6px;background:#fff2d7;color:#966000}.tag.high{background:#ffebed;color:#b52d3c}.tag.low{background:#e4f7f0;color:#147c65}.flash{padding:10px 14px;border-radius:8px;margin:10px 0;background:#e4f7f0;color:#146e5b}.finding{margin-bottom:12px}.finding h3{margin:10px 0 3px}.evidence,.suggestion{padding:12px;border-radius:8px;background:#f3f6fa;margin-top:9px;font-size:13px}.suggestion{background:#e8f7f4}.history{display:grid;grid-template-columns:2fr 1fr 1.5fr;gap:12px;padding:12px;border-top:1px solid #edf0f5;font-size:12px}.status{font-size:10px;font-weight:800;background:#edf3ff;color:#3159a8;padding:5px 8px;border-radius:6px}.foot{padding:28px 0;color:#637187;font-size:11px;border-top:1px solid #dce4ee;margin-top:20px}.buttons{display:flex;gap:8px;flex-wrap:wrap}.draft{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8fc;padding:12px;border-radius:8px;font:13px/1.6 monospace}.notice{padding:12px;background:#eef4ff;border:1px solid #dbe6fb;border-radius:9px;font-size:12px;margin:18px 0}@media(max-width:720px){.bar{align-items:flex-start;flex-direction:column}.hero,.two{grid-template-columns:1fr}.hero h1{font-size:43px}.stats{gap:7px}.stats .card{padding:12px}.stats strong{font-size:18px}.wrap{padding:0 15px}.bar nav{flex-wrap:wrap}.history{grid-template-columns:1fr 1fr}.history span:last-child{grid-column:1/-1}}"""
HEAD="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BrandShield AI</title><style>"""+CSS+"""</style></head><body><header class="bar"><a class="brand" href="/">▣ BrandShield <b>AI</b></a><nav><a href="/#review">Review content</a><a href="/#rules">Brand knowledge</a><a href="/#history">History</a></nav></header><main class="wrap">"""
FOOT="""<footer class="foot">Cognify · Rules-first prototype · AI findings are suggestions, not approval.</footer></main></body></html>"""
@app.route("/")
def home():
 rules=rows("rules");facts=rows("facts");c=conn();recent=[dict(x) for x in c.execute("SELECT id,title,status,created FROM reviews ORDER BY id DESC LIMIT 8")];c.close()
 return render_template_string(HEAD+"""
<section class="hero"><div><p class="eyebrow">COGNIFY · ROUND 2 MVP</p><h1>Keep every message<br><span>on brand.</span></h1><p class="muted">Check draft content against approved rules, understand findings, revise with control, and record a human decision.</p><a class="btn" href="#review">Review a draft →</a><p><small>Rules-first prototype. A clean check is not a guarantee of accuracy or compliance.</small></p></div><div class="panel"><p class="eyebrow">REVIEW SNAPSHOT</p><h3>Unsupported claim · HIGH</h3><p>“No. 1 in India”</p><hr><h3>Evidence needed</h3><p>No approved source found in the demo knowledge base.</p><hr><h3>Human decision</h3><p>Final approval stays with the reviewer.</p></div></section>
{% with msgs=get_flashed_messages() %}{% for m in msgs %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}
<div class="stats"><div class="card"><strong>{{rules|length}}</strong><small>Active rules</small></div><div class="card"><strong>{{facts|length}}</strong><small>Approved fact notes</small></div><div class="card"><strong>Human</strong><small>Final approval</small></div></div>
<section id="review" class="section"><p class="eyebrow">01 / CONTENT CHECK</p><h2>Review a draft</h2><p class="muted">Paste a social post, promotion, email, or campaign message.</p><form class="card" action="/review" method="post"><label>Draft name</label><input name="title" placeholder="e.g. October campaign"><label>Content to review *</label><textarea id="content" name="content" rows="7" required placeholder="Paste your draft..."></textarea><button class="btn">Run brand review →</button> <button class="btn alt" type="button" onclick="document.querySelector('[name=title]').value='Sample campaign';document.getElementById('content').value='We are the No. 1 tool in India with guaranteed results. Our product is free for everyone. Act now or regret it!'">Load sample content</button></form></section>
<section id="rules" class="section"><p class="eyebrow">02 / BRAND KNOWLEDGE</p><h2>Configure rules and facts</h2><div class="two"><form class="card" action="/rules" method="post"><h3>Add a rule</h3><label>Category</label><select name="category"><option value="prohibited_term">Prohibited phrase</option><option value="required_phrase">Required phrase</option><option value="tone">Tone guidance</option><option value="disclaimer">Claim evidence</option></select><label>Rule explanation *</label><input name="rule_text" required><label>Trigger phrase (optional)</label><input name="trigger_text"><label>Severity</label><select name="severity"><option>low</option><option selected>medium</option><option>high</option></select><button class="btn">+ Add rule</button></form><form class="card" action="/facts" method="post"><h3>Add approved fact</h3><label>Fact title *</label><input name="title" required><label>Approved wording *</label><textarea name="fact_text" rows="4" required></textarea><button class="btn">+ Add fact</button></form></div>
<div class="two"><div class="card"><h3>Active rules ({{rules|length}})</h3>{% for r in rules %}<div class="row"><div><b>{{r.category.replace('_',' ')|title}}</b><p>{{r.rule_text}}</p>{% if r.trigger_text %}<small>Trigger: {{r.trigger_text}}</small>{% endif %}</div><span class="tag {{r.severity}}">{{r.severity}}</span></div>{% endfor %}</div><div class="card"><h3>Approved facts ({{facts|length}})</h3>{% for f in facts %}<div class="row"><div><b>{{f.title}}</b><p>{{f.fact_text}}</p></div></div>{% endfor %}</div></div></section>
<section id="history" class="section"><p class="eyebrow">03 / ACCOUNTABILITY</p><h2>Recent reviews</h2><div class="card">{% if recent %}{% for r in recent %}<a class="history" href="/review/{{r.id}}"><b>{{r.title}}</b><span class="status">{{r.status}}</span><span>{{r.created}}</span></a>{% endfor %}{% else %}<p class="muted">No reviews yet.</p>{% endif %}</div></section>"""+FOOT,rules=rules,facts=facts,recent=recent)
@app.route("/rules",methods=["POST"])
def add_rule():
 cat=request.form.get("category","prohibited_term");txt=request.form.get("rule_text","").strip();tr=request.form.get("trigger_text","").strip();sev=request.form.get("severity","medium").lower()
 if cat not in {"prohibited_term","required_phrase","tone","disclaimer"}:cat="prohibited_term"
 if sev not in {"low","medium","high"}:sev="medium"
 if not txt:flash("Rule explanation is required.");return redirect("/#rules")
 c=conn();c.execute("INSERT INTO rules(category,rule_text,trigger_text,severity) VALUES(?,?,?,?)",(cat,txt,tr,sev));c.commit();c.close();flash("Brand rule added.");return redirect("/#rules")
@app.route("/facts",methods=["POST"])
def add_fact():
 title=request.form.get("title","").strip();txt=request.form.get("fact_text","").strip()
 if not title or not txt:flash("Both fact fields are required.");return redirect("/#rules")
 c=conn();c.execute("INSERT INTO facts(title,fact_text) VALUES(?,?)",(title,txt));c.commit();c.close();flash("Approved fact added.");return redirect("/#rules")
@app.route("/review",methods=["POST"])
def review():
 title=request.form.get("title","").strip() or "Untitled content";text=request.form.get("content","").strip()
 if not text:flash("Paste content first.");return redirect("/")
 findings=analyse(text);ai,msg=optional_ai(text,findings)
 if ai:findings.append(dict(category="Optional AI tone review",severity="medium",matched_text="Whole draft",explanation=str(ai.get("tone_observation","")),evidence="AI observation; verify manually.",suggestion=str(ai.get("suggested_rewrite","")),status="Human review required"))
 now=datetime.now().isoformat(timespec="seconds");c=conn();cur=c.execute("INSERT INTO reviews(title,content,findings,status,created,updated) VALUES(?,?,?,?,?,?)",(title,text,json.dumps(findings), "In review",now,now));rid=cur.lastrowid;c.commit();c.close()
 return render_template_string(HEAD+REVIEW+FOOT,rid=rid,title=title,text=text,findings=findings,suggestion=rewrite(text),ai_status=msg,status="In review",note="")
@app.route("/review/<int:rid>")
def detail(rid):
 c=conn();r=c.execute("SELECT * FROM reviews WHERE id=?",(rid,)).fetchone();c.close()
 if not r:return "Review not found",404
 return render_template_string(HEAD+REVIEW+FOOT,rid=rid,title=r["title"],text=r["content"],findings=json.loads(r["findings"]),suggestion=rewrite(r["content"]),ai_status="Saved review record.",status=r["status"],note=r["note"])
REVIEW="""<p class="eyebrow">REVIEW ID #{{rid}}</p><h1>{{title}}</h1><p class="muted">Findings are decision support, not automatic approval.</p><div class="notice"><b>Analysis mode:</b> {{ai_status}} Core checks work without an AI key.</div><section class="section"><h2>Findings</h2>{% for f in findings %}<article class="card finding"><div class="sectionhead"><b>{{f.category}}</b><span class="tag {{f.severity}}">{{f.severity}}</span></div><h3>{{f.matched_text}}</h3><p>{{f.explanation}}</p><div class="evidence"><b>Evidence / rule</b><p>{{f.evidence}}</p></div><div class="suggestion"><b>Suggested action</b><p>{{f.suggestion}}</p></div><small>{{f.status}}</small></article>{% endfor %}</section><section class="section"><h2>Original and suggested revision</h2><div class="two"><div class="card"><h3>Original</h3><pre class="draft">{{text}}</pre></div><div class="card"><h3>Suggested rewrite (editable)</h3><textarea id="suggestion" rows="8">{{suggestion}}</textarea><button class="btn alt" type="button" onclick="document.getElementById('newtext').value=document.getElementById('suggestion').value">Use suggestion ↓</button></div></div><form class="card" method="post" action="/revise/{{rid}}"><label>Revision title</label><input name="title" value="{{title}} — revision"><label>Revised content</label><textarea id="newtext" name="content" rows="7" required>{{text}}</textarea><button class="btn">Re-check as new revision →</button></form></section><section class="section"><h2>Human review decision</h2><form class="card" action="/decision/{{rid}}" method="post"><label>Reviewer note</label><textarea name="note" rows="3">{{note}}</textarea><div class="buttons"><button class="btn alt" name="status" value="Changes requested">Request changes</button><button class="btn alt" name="status" value="Rejected">Reject</button><button class="btn" name="status" value="Approved">Approve</button></div><p><small>Approve only after checking relevant approved sources.</small></p></form><p>Current status: <span class="status">{{status}}</span> · <a href="/export/{{rid}}">Export review JSON</a></p></section>"""
@app.route("/decision/<int:rid>",methods=["POST"])
def decision(rid):
 status=request.form.get("status","");note=request.form.get("note","").strip()
 if status not in {"Approved","Changes requested","Rejected"}:return "Invalid status",400
 c=conn();c.execute("UPDATE reviews SET status=?,note=?,updated=? WHERE id=?",(status,note,datetime.now().isoformat(timespec="seconds"),rid));c.commit();c.close();flash("Human decision saved.");return redirect(url_for("detail",rid=rid))
@app.route("/revise/<int:rid>",methods=["POST"])
def revise(rid):
 title=request.form.get("title","Revised content").strip();text=request.form.get("content","").strip()
 if not text:return "Revision cannot be empty",400
 f=analyse(text);now=datetime.now().isoformat(timespec="seconds");c=conn();cur=c.execute("INSERT INTO reviews(title,content,findings,status,created,updated) VALUES(?,?,?,?,?,?)",(title,text,json.dumps(f),"In review",now,now));newid=cur.lastrowid;c.commit();c.close();flash(f"Revision saved as review #{newid}; original preserved.");return redirect(url_for("detail",rid=newid))
@app.route("/export/<int:rid>")
def export(rid):
 c=conn();r=c.execute("SELECT * FROM reviews WHERE id=?",(rid,)).fetchone();c.close()
 if not r:return "Not found",404
 d=dict(r);d["findings"]=json.loads(d.pop("findings"));return jsonify(d)
@app.route("/api/health")
def health():return jsonify(status="ok",product="BrandShield AI",mode="rules-first MVP",optional_ai_configured=bool(os.environ.get("GEMINI_API_KEY")))
init()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")),debug=False)
