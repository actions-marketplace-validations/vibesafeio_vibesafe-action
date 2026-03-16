import os, sqlite3, subprocess
from flask import Flask, request, jsonify
app = Flask(__name__)
API_KEY = "sk-proj-abc123def456ghi789jkl012"

@app.route("/search")
def search():
    q = request.args.get("q", "")
    db = sqlite3.connect("test.db")
    sql = f"SELECT * FROM users WHERE name LIKE '%{q}%'"
    return jsonify(db.execute(sql).fetchall())

@app.route("/run", methods=["POST"])
def run_cmd():
    cmd = request.json.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return jsonify({"out": result.stdout})

@app.route("/eval", methods=["POST"])
def do_eval():
    return jsonify({"result": str(eval(request.json.get("expr")))})
