"""
CodeSage AI -- Post-Fix Verification + Accuracy Assessment
Runs after all 4 bugs are fixed.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import json
import os
import glob
import time

BASE = "http://localhost:8000"
RESULTS = {}
ACCURACY = {}

def section(title):
    print("\n" + "="*70)
    print("  " + title)
    print("="*70)

def check(label, condition, evidence=""):
    status = "[PASS]" if condition else "[FAIL]"
    print("  {}  {}".format(status, label))
    if evidence:
        print("         Evidence: {}".format(str(evidence)[:250]))
    return condition

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
section("PRE-CHECK: Server Health")
try:
    r = requests.get("{}/health".format(BASE), timeout=5)
    check("Server responding", r.status_code == 200)
except:
    print("  [FATAL] Server unreachable")
    sys.exit(1)

# Get repos
r = requests.get("{}/api/repository/list".format(BASE), timeout=5)
repos = r.json().get("repositories", [])
completed = [repo for repo in repos if repo["status"] == "completed"]
REPO_ID = completed[0]["id"] if completed else None
print("  Using repo_id={}".format(REPO_ID))

# =================================================
# USP 1 -- Context-Aware Debugging (RAG)
# =================================================
section("USP 1 -- Context-Aware Debugging (RAG Pipeline)")
usp1 = []

if REPO_ID:
    r = requests.post("{}/api/debug/analyze".format(BASE), json={
        "error": "TypeError: Cannot read property 'map' of undefined",
        "repo_id": REPO_ID
    }, timeout=90)
    print("  HTTP {}".format(r.status_code))
    if r.status_code == 200:
        d = r.json()
        ctx = d.get("context_used", [])
        usp1.append(check("All response fields present",
            all(k in d for k in ["root_cause","explanation","suggested_fix","code_patch","severity","category"])))
        usp1.append(check("context_used populated", len(ctx) > 0, "count={}".format(len(ctx))))
        usp1.append(check("Scores are positive", all(c.get("score",0)>0 for c in ctx),
            "scores={}".format([c.get("score") for c in ctx])))
        usp1.append(check("Files are deduplicated (unique paths)",
            len(ctx) == len(set(c["file_path"] for c in ctx)),
            "files={}".format([c["file_path"] for c in ctx])))
        usp1.append(check("Explanation is substantive", len(d.get("explanation","")) > 50))
        print("  root_cause: {}".format(d.get("root_cause","")[:200]))
    else:
        usp1.append(check("Debug call succeeds", False, "HTTP {}".format(r.status_code)))

RESULTS["USP1"] = usp1

# =================================================
# USP 2 -- Semantic Code Search (FAISS)
# =================================================
section("USP 2 -- Semantic Code Search (Deduplication Verified)")
usp2 = []

queries = [
    ("authentication middleware handling", "auth"),
    ("database connection pool", "db"),
    ("error handling try catch", "error"),
    ("user login token validation", "auth_synonym"),
]

for query, label in queries:
    r = requests.post("{}/api/search".format(BASE), json={"query": query, "top_k": 5}, timeout=30)
    print("\n  Query: '{}'".format(query))
    if r.status_code == 200:
        results = r.json().get("results", [])
        files = [res.get("file_path") for res in results]
        scores = [res.get("score") for res in results]
        usp2.append(check("Results returned (n={})".format(len(results)), len(results) > 0))
        
        # KEY CHECK: no duplicate file paths
        unique_files = len(set(files))
        usp2.append(check("Results are deduplicated ({} unique of {})".format(unique_files, len(files)),
            unique_files == len(files), "files={}".format(files[:5])))
        
        usp2.append(check("Scores descending", 
            all(scores[i] >= scores[i+1] for i in range(len(scores)-1)) if len(scores) > 1 else True))
        
        if label == "db":
            has_db = any("db" in f.lower() or "database" in f.lower() for f in files)
            usp2.append(check("'database connection' finds db-related file", has_db, "files={}".format(files[:3])))
            ACCURACY["search_db"] = has_db
        
        if label == "error":
            has_error = any("error" in f.lower() or "debug" in f.lower() or "route" in f.lower() for f in files)
            usp2.append(check("'error handling' finds relevant file", has_error, "files={}".format(files[:3])))
            ACCURACY["search_error"] = has_error

        print("  Files: {}".format(files[:5]))
        print("  Scores: {}".format(scores[:5]))
    else:
        usp2.append(check("Search works", False))

# Empty query
r = requests.post("{}/api/search".format(BASE), json={"query": ""}, timeout=5)
usp2.append(check("Empty query -> 400", r.status_code == 400))

RESULTS["USP2"] = usp2

# =================================================
# USP 3 -- Full Pipeline
# =================================================
section("USP 3 -- End-to-End Pipeline Verification")
usp3 = []

# FAISS on disk
vdb = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vector_db")
idx = glob.glob(os.path.join(vdb, "repo_*.index"))
usp3.append(check("FAISS indexes exist", len(idx) > 0))
for f in idx:
    usp3.append(check("Index {} > 10KB".format(os.path.basename(f)), os.path.getsize(f) > 10000))

# Full pipeline
if REPO_ID:
    r = requests.post("{}/api/debug/analyze".format(BASE), json={
        "error": "NullPointerException in UserService.getUser at line 42",
        "repo_id": REPO_ID
    }, timeout=90)
    if r.status_code == 200:
        d = r.json()
        for k in ["root_cause", "explanation", "suggested_fix", "code_patch", "severity", "category"]:
            usp3.append(check("Has '{}'".format(k), k in d and bool(d[k])))
        usp3.append(check("context_used non-empty", len(d.get("context_used",[])) > 0))
        usp3.append(check("severity valid", d.get("severity") in ["low","medium","high","critical"]))
        
        # Accuracy: does root_cause make sense?
        rc = d.get("root_cause","").lower()
        ACCURACY["debug_relevant"] = "null" in rc or "undefined" in rc or "not found" in rc or "exception" in rc
        usp3.append(check("Root cause mentions null/exception", ACCURACY["debug_relevant"],
            "root_cause={}".format(d.get("root_cause","")[:120])))

RESULTS["USP3"] = usp3

# =================================================
# USP 4 -- LLM Provider (now with dual support)
# =================================================
section("USP 4 -- LLM Provider Verification (Groq + Ollama Support)")
usp4 = []

# Read config
llm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "rag", "llm_client.py")
with open(llm_path, encoding="utf-8") as f:
    code = f.read()

has_groq = "_generate_groq" in code
has_ollama = "_generate_ollama" in code
has_provider_switch = "LLM_PROVIDER" in code

usp4.append(check("llm_client.py has Groq provider", has_groq))
usp4.append(check("llm_client.py has Ollama provider", has_ollama))
usp4.append(check("Provider switching via LLM_PROVIDER", has_provider_switch))

# Verify current provider works (should be groq based on .env)
r = requests.post("{}/api/debug/analyze".format(BASE), json={
    "error": "IndexError: list index out of range"
}, timeout=60)
usp4.append(check("Active LLM provider responds", r.status_code == 200,
    "HTTP {} root_cause={}".format(r.status_code, r.json().get("root_cause","")[:100] if r.status_code == 200 else r.text[:100])))

# Verify Ollama health check endpoint exists in code
has_health_check = "_check_ollama_health" in code
usp4.append(check("Ollama health check implemented", has_health_check))

# Verify ConnectionError -> 503 mapping exists in debug_routes
debug_routes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "api", "debug_routes.py")
with open(debug_routes_path, encoding="utf-8") as f:
    dr_code = f.read()
usp4.append(check("ConnectionError -> 503 mapping in debug_routes", "ConnectionError" in dr_code))

RESULTS["USP4"] = usp4

# =================================================
# USP 5 -- Production Engineering
# =================================================
section("USP 5 -- Production-Level Engineering (Robustness)")
usp5 = []

# Duplicate repo
if completed:
    r = requests.post("{}/api/repository/connect".format(BASE), json={"repo_url": completed[0]["url"]}, timeout=10)
    usp5.append(check("Duplicate repo -> 409", r.status_code == 409))

# Invalid URL
r = requests.post("{}/api/repository/connect".format(BASE), json={"repo_url": "not-a-url"}, timeout=5)
usp5.append(check("Invalid URL -> 400", r.status_code == 400))

# Empty error
r = requests.post("{}/api/debug/analyze".format(BASE), json={"error": "   "}, timeout=5)
usp5.append(check("Empty error -> 400", r.status_code == 400))

# Empty search
r = requests.post("{}/api/search".format(BASE), json={"query": ""}, timeout=5)
usp5.append(check("Empty search -> 400", r.status_code == 400))

# 404
r = requests.get("{}/api/repository/99999/status".format(BASE), timeout=5)
usp5.append(check("Missing repo -> 404", r.status_code == 404))

# Still alive
r = requests.get("{}/health".format(BASE), timeout=5)
usp5.append(check("Server alive after all tests", r.status_code == 200))

# WAL mode
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "database", "db.py")
with open(db_path, encoding="utf-8") as f:
    db_code = f.read()
usp5.append(check("WAL mode enabled in db.py", "journal_mode=WAL" in db_code))
usp5.append(check("busy_timeout configured", "busy_timeout" in db_code))

# Activity retry logic
act_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "services", "activity_service.py")
with open(act_path, encoding="utf-8") as f:
    act_code = f.read()
usp5.append(check("Activity save has retry logic", "MAX_SAVE_RETRIES" in act_code))

RESULTS["USP5"] = usp5

# =================================================
# ACTIVITY SAVE VERIFICATION (Bug 2 specific)
# =================================================
section("BUG 2 VERIFICATION -- Activity Saving No Longer Fails")
# After a debug call, activity should be saved
time.sleep(2)  # Wait for async save
r = requests.get("{}/api/activity".format(BASE), timeout=10)
if r.status_code == 200:
    activities = r.json().get("activities", [])
    check("Activities exist in DB", len(activities) > 0, "count={}".format(len(activities)))
    if activities:
        latest = activities[0]
        check("Latest activity has root_cause", bool(latest.get("root_cause")))
        check("Latest activity has error", bool(latest.get("error")))
        print("  Latest: error='{}' | severity={}".format(
            latest.get("error","")[:80], latest.get("severity")))

# =================================================
# CHAT FEATURE VERIFICATION
# =================================================
section("CHAT FEATURE -- RAG Chatbot Verification")
# Casual message
r = requests.post("{}/api/chat/ask".format(BASE), json={"message": "hello"}, timeout=30)
print("  Casual msg 'hello' -> HTTP {}".format(r.status_code))
if r.status_code == 200:
    d = r.json()
    check("Casual reply present", bool(d.get("reply")))
    check("No sources for casual msg", len(d.get("sources",[])) == 0)
    print("  Reply: {}".format(d.get("reply","")[:150]))

# Code question
if REPO_ID:
    r = requests.post("{}/api/chat/ask".format(BASE), json={
        "message": "How does the debug analysis pipeline work?",
        "repo_id": REPO_ID
    }, timeout=60)
    print("\n  Code question -> HTTP {}".format(r.status_code))
    if r.status_code == 200:
        d = r.json()
        check("Code reply present", bool(d.get("reply")))
        check("Sources returned for code question", len(d.get("sources",[])) > 0)
        print("  Reply (first 200): {}".format(d.get("reply","")[:200]))
        print("  Sources: {}".format([s["file_path"] for s in d.get("sources",[])]))

# =================================================
# ACCURACY ASSESSMENT
# =================================================
section("ACCURACY ASSESSMENT")

# 1. Retrieval precision test
precision_tests = [
    ("database initialization and schema", ["db.py", "database"]),
    ("embedding generation model loading", ["embedding", "model"]),
    ("git clone repository", ["git", "clone", "repo"]),
    ("FAISS vector search index", ["vector", "faiss", "search"]),
    ("code chunking text splitter", ["chunk", "split"]),
]

retrieval_hits = 0
total_tests = len(precision_tests)

for query, expected_keywords in precision_tests:
    r = requests.post("{}/api/search".format(BASE), json={"query": query, "top_k": 3}, timeout=30)
    if r.status_code == 200:
        results = r.json().get("results", [])
        if results:
            top_file = results[0].get("file_path", "").lower()
            hit = any(kw in top_file for kw in expected_keywords)
            if hit:
                retrieval_hits += 1
            check("'{}' -> top file relevant".format(query[:40]),
                hit, "top_file={}".format(results[0].get("file_path")))

retrieval_precision = retrieval_hits / total_tests if total_tests > 0 else 0
ACCURACY["retrieval_precision"] = retrieval_precision
print("\n  Retrieval Precision@1: {:.0f}% ({}/{})".format(retrieval_precision*100, retrieval_hits, total_tests))

# 2. LLM Response Quality
quality_tests = [
    "TypeError: Cannot read property 'length' of undefined",
    "ModuleNotFoundError: No module named 'flask'",
    "CORS policy: No 'Access-Control-Allow-Origin' header",
]

quality_hits = 0
for error in quality_tests:
    r = requests.post("{}/api/debug/analyze".format(BASE), json={"error": error}, timeout=60)
    if r.status_code == 200:
        d = r.json()
        rc = d.get("root_cause", "")
        fix = d.get("suggested_fix", "")
        has_quality = len(rc) > 20 and len(fix) > 20 and rc != "Analysis not available"
        if has_quality:
            quality_hits += 1
        check("Quality for '{}'".format(error[:40]), has_quality,
            "root_cause_len={}, fix_len={}".format(len(rc), len(fix)))

llm_quality = quality_hits / len(quality_tests)
ACCURACY["llm_quality"] = llm_quality
print("\n  LLM Response Quality: {:.0f}% ({}/{})".format(llm_quality*100, quality_hits, len(quality_tests)))

# 3. Overall accuracy
overall = (retrieval_precision * 0.4 + llm_quality * 0.4 + 
           (1.0 if ACCURACY.get("search_db") else 0) * 0.1 +
           (1.0 if ACCURACY.get("debug_relevant") else 0) * 0.1)
ACCURACY["overall"] = overall

# =================================================
# FINAL SUMMARY
# =================================================
section("FINAL RESULTS")

labels = {
    "USP1": "Context-Aware Debugging (RAG)",
    "USP2": "Semantic Code Search (Deduplicated)",
    "USP3": "End-to-End AI Pipeline",
    "USP4": "LLM Integration (Groq + Ollama)",
    "USP5": "Production Engineering",
}

print("\n  {:<8} {:<42} {}".format("USP", "Feature", "Result"))
print("  " + "-"*65)
for key, label in labels.items():
    tests = RESULTS.get(key, [])
    if tests:
        p = sum(1 for t in tests if t)
        t = len(tests)
        pct = p/t
        if pct >= 0.85:
            v = "ACHIEVED ({}/{})".format(p,t)
        elif pct >= 0.5:
            v = "PARTIAL ({}/{})".format(p,t)
        else:
            v = "NOT ACHIEVED ({}/{})".format(p,t)
    else:
        v = "NO DATA"
    print("  {:<8} {:<42} {}".format(key, label[:41], v))

print("\n" + "="*70)
print("  ACCURACY SCORES")
print("="*70)
print("  Retrieval Precision@1:  {:.0f}%".format(ACCURACY.get("retrieval_precision",0)*100))
print("  LLM Response Quality:   {:.0f}%".format(ACCURACY.get("llm_quality",0)*100))
print("  Semantic Relevance:     {}".format("PASS" if ACCURACY.get("search_db") else "FAIL"))
print("  Debug Relevance:        {}".format("PASS" if ACCURACY.get("debug_relevant") else "FAIL"))
print("  -----------------------------------------")
print("  OVERALL ACCURACY:       {:.0f}%".format(ACCURACY.get("overall",0)*100))
print("="*70)

print("\nVerification complete.")
