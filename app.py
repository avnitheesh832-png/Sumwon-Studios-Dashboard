"""
Sumwon Studios — Performance Dashboard
Flask app: upload page + live dashboard
"""
import os
import json
from flask import (Flask, request, redirect, url_for,
                   render_template, jsonify, session, send_from_directory)
from processor import process_files

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-in-production')

# Where to store processed data (Railway Volume mounts to /data)
DATA_DIR  = os.environ.get('DATA_DIR', '/tmp/sumwon_data')
DATA_FILE = os.path.join(DATA_DIR, 'dashboard_data.json')
UPLOAD_PASSWORD = os.environ.get('UPLOAD_PASSWORD', 'sumwon2026')

REQUIRED_FILES = {
    'table1':   'Weekly_Trade_Table_1',
    'table2':   'Weekly_Trade_Table_2',
    'cohort':   'Weekly_Trade_Cohort',
    'webshop':  'Webshop_per_Site_per_Week',
}


def data_exists():
    return os.path.exists(DATA_FILE)


def load_data():
    if data_exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return None


def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)


# ── ROUTES ──────────────────────────────────────────────────

@app.route('/')
def index():
    if data_exists():
        return redirect(url_for('dashboard'))
    return redirect(url_for('upload'))


@app.route('/dashboard')
def dashboard():
    if not data_exists():
        return redirect(url_for('upload'))
    d = load_data()
    meta = {
        'weeks':   d.get('weeks', []),
        'updated': d.get('updated', ''),
        'hr_wk':   d.get('hr_wk', ''),
    }
    return render_template('dashboard.html', meta=meta)


@app.route('/api/data')
def api_data():
    d = load_data()
    if not d:
        return jsonify({'error': 'No data uploaded yet'}), 404
    return jsonify(d)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    error = None
    success = None

    if request.method == 'POST':
        # Password check
        pwd = request.form.get('password', '')
        if pwd != UPLOAD_PASSWORD:
            error = 'Incorrect password.'
            return render_template('upload.html', error=error, success=None,
                                   has_data=data_exists())

        # Check all 4 files present
        files = {}
        missing = []
        for key in REQUIRED_FILES:
            f = request.files.get(key)
            if not f or f.filename == '':
                missing.append(REQUIRED_FILES[key])
            else:
                files[key] = f.read()

        if missing:
            error = f"Missing files: {', '.join(missing)}"
            return render_template('upload.html', error=error, success=None,
                                   has_data=data_exists())

        # Process
        try:
            data = process_files(
                table1_bytes  = files['table1'],
                table2_bytes  = files['table2'],
                cohort_bytes  = files['cohort'],
                webshop_bytes = files['webshop'],
            )
            save_data(data)
            weeks = data.get('weeks', [])
            success = (f"Dashboard updated. "
                       f"{len(weeks)} weeks loaded "
                       f"({weeks[0]} to {weeks[-1]}).")
        except Exception as e:
            error = f"Processing error: {str(e)}"

    return render_template('upload.html', error=error, success=success,
                           has_data=data_exists())


@app.route('/upload/clear', methods=['POST'])
def clear_data():
    pwd = request.form.get('password', '')
    if pwd != UPLOAD_PASSWORD and not session.get('admin'):
        return redirect(url_for('upload'))
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    return redirect(url_for('upload'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port,
            debug=os.environ.get('DEBUG', 'false').lower() == 'true')
