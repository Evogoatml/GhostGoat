from flask import Flask, render_template_string, request
import os
from adap.plugins import git_interface
from adap.plugins import learning_agent
from adap.plugins import hf_llm

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ADAP Control Dashboard</title>
<style>
body { font-family: Arial, sans-serif; background:#0d1117; color:#c9d1d9; text-align:center; }
button { background:#238636; color:white; border:none; padding:10px 20px; margin:10px; cursor:pointer; border-radius:6px; }
input { width:60%; padding:8px; border-radius:6px; border:1px solid #30363d; background:#161b22; color:white; }
textarea { width:80%; height:260px; background:#161b22; color:#fff; border:1px solid #30363d; border-radius:6px; padding:10px; }
</style>
</head>
<body>
<h1>🧠 ADAP Control Dashboard</h1>

<form method="post" action="/clone">
  <input type="text" name="repo" placeholder="GitHub URL (e.g., https://github.com/Netflix/metaflow.git)">
  <button type="submit">Clone Repo</button>
</form>

<form method="post" action="/learn">
  <input type="text" name="topic" placeholder="Teach ADAP something new">
  <button type="submit">Learn</button>
</form>

<form method="get" action="/learned">
  <button type="submit">View Learned Topics</button>
</form>

<form method="post" action="/hfllm">
  <input type="text" name="prompt" placeholder="Ask HuggingFace LLM">
  <button type="submit">Query HF LLM</button>
</form>

{% if output %}
<h2>Output</h2>
<textarea readonly>{{ output }}</textarea>
{% endif %}
</body>
</html>
"""
@app.route("/hfllm", methods=["POST"])
def hfllm_route():
    prompt = request.form.get("prompt", "")
    if not prompt:
        out = "No prompt provided."
    else:
        out = hf_llm.ask(prompt)
    return render_template_string(HTML, output=out)

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML)

@app.route("/clone", methods=["POST"])
def clone():
    repo = request.form.get("repo")
    if not repo:
        out = "⚠️ No repository provided."
    else:
        from io import StringIO
        import sys
        buf = StringIO()
        sys_stdout = sys.stdout
        sys.stdout = buf
        try:
            git_interface.clone_repo(repo)  # uses your existing plugin12
        finally:
            sys.stdout = sys_stdout
        out = buf.getvalue()
    return render_template_string(HTML, output=out)

@app.route("/learn", methods=["POST"])
def learn():
    topic = request.form.get("topic", "")
    from io import StringIO
    import sys
    buf = StringIO()
    sys_stdout = sys.stdout
    sys.stdout = buf
    try:
        learning_agent.learn_topic(topic)
    finally:
        sys.stdout = sys_stdout
    out = buf.getvalue()
    return render_template_string(HTML, output=out)

@app.route("/learned", methods=["GET"])
def learned():
    from io import StringIO
    import sys
    buf = StringIO()
    sys_stdout = sys.stdout
    sys.stdout = buf
    try:
        learning_agent.list_learnings()
    finally:
        sys.stdout = sys_stdout
    out = buf.getvalue()
    return render_template_string(HTML, output=out)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 ADAP Dashboard running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
