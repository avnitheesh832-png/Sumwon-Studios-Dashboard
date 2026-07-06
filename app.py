"""
Sumwon Studios — Performance Dashboard
Flask app: upload page + live dashboard + CEO email
"""
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import (Flask, request, redirect, url_for,
                   render_template, jsonify)
from processor import process_files

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-in-production')

DATA_DIR         = os.environ.get('DATA_DIR', '/tmp/sumwon_data')
DATA_FILE        = os.path.join(DATA_DIR, 'dashboard_data.json')
UPLOAD_PASSWORD  = os.environ.get('UPLOAD_PASSWORD', 'sumwon2026')
CEO_EMAIL        = 'nitin@sumwonstudio.com'
DASHBOARD_URL    = os.environ.get('DASHBOARD_URL', 'https://web-production-f7c11.up.railway.app')

REQUIRED_FILES = {
    'table1':  'Weekly_Trade_Table_1',
    'table2':  'Weekly_Trade_Table_2',
    'cohort':  'Weekly_Trade_Cohort',
    'webshop': 'Webshop_per_Site_per_Week',
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


# ── EMAIL ────────────────────────────────────────────────────

def build_email_html(data, week_label):
    """Build a clean CEO summary email."""
    weeks = data.get('weeks', [])
    latest_wk = weeks[-1] if weeks else None
    brands_data = data['data'].get(latest_wk, {}) if latest_wk else {}

    # Calculate portfolio totals
    total_sr = sum(brands_data.get(b, {}).get('sr', 0) or 0 for b in data.get('brands', []))
    total_wr = sum(brands_data.get(b, {}).get('wr', 0) or 0 for b in data.get('brands', []))
    total_rev = total_sr + total_wr
    total_sp = sum(brands_data.get(b, {}).get('sp', 0) or 0 for b in data.get('brands', []))
    pc2 = round(total_sp / total_sr * 100, 1) if total_sr else 0

    WEB_IDS = ['MISSGUIDED', 'AiiRZ', 'KIZN', 'SUMWON - Women']
    web_rev    = sum(brands_data.get(b, {}).get('w_rev', 0) or 0 for b in WEB_IDS)
    web_orders = sum(brands_data.get(b, {}).get('w_orders', 0) or 0 for b in WEB_IDS)
    web_roas_vals = [brands_data.get(b, {}).get('w_roas') for b in WEB_IDS if brands_data.get(b, {}).get('w_roas')]
    web_roas = round(sum(web_roas_vals) / len(web_roas_vals), 2) if web_roas_vals else None

    def fm(v):
        if not v: return '-'
        if abs(v) >= 1000000: return f'${v/1000000:.2f}M'
        if abs(v) >= 1000: return f'${round(v/1000)}K'
        return f'${round(v):,}'

    # HR data
    hr_wk = data.get('hr_wk', '')
    hr_brands = data['data'].get(hr_wk, {}) if hr_wk else {}
    hrs = [hr_brands.get(b, {}).get('hrt') for b in data.get('brands', []) if hr_brands.get(b, {}).get('hrt') is not None]
    avg_hr = round(sum(hrs)/len(hrs), 1) if hrs else None

    updated = data.get('updated', datetime.utcnow().strftime('%d %b %Y'))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#F3F2EF;font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:32px 16px">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;border:1px solid #D9D8D2">

  <!-- Header -->
  <tr><td style="background:#0C0C0E;padding:20px 28px">
    <div style="font-size:9px;font-weight:500;letter-spacing:.14em;text-transform:uppercase;color:#555;margin-bottom:4px">Sumwon Studios</div>
    <div style="font-size:18px;font-weight:600;color:#fff">Weekly Performance Dashboard</div>
    <div style="font-size:12px;color:#888;margin-top:4px">{week_label} &nbsp;&middot;&nbsp; {updated}</div>
  </td></tr>

  <!-- Total Performance -->
  <tr><td style="padding:0">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr style="background:#F3F2EF">
        <td style="padding:8px 28px;font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8C8A86;border-bottom:1px solid #D9D8D2">
          Total Performance
        </td>
      </tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td width="33%" style="padding:16px 28px;border-right:1px solid #ECEAE5">
          <div style="font-size:9px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#8C8A86;margin-bottom:6px">Total Revenue</div>
          <div style="font-size:24px;font-weight:600;color:#0C0C0E">{fm(total_rev)}</div>
        </td>
        <td width="33%" style="padding:16px 28px;border-right:1px solid #ECEAE5">
          <div style="font-size:9px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#8C8A86;margin-bottom:6px">SHEIN Revenue</div>
          <div style="font-size:24px;font-weight:600;color:#0C0C0E">{fm(total_sr)}</div>
        </td>
        <td width="33%" style="padding:16px 28px">
          <div style="font-size:9px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#8C8A86;margin-bottom:6px">Webshop Revenue</div>
          <div style="font-size:24px;font-weight:600;color:#0C0C0E">{fm(total_wr)}</div>
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- SHEIN + Webshop KPIs -->
  <tr><td style="padding:0;border-top:1px solid #ECEAE5">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td width="25%" style="padding:14px 28px;border-right:1px solid #ECEAE5">
          <div style="font-size:9px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#8C8A86;margin-bottom:4px">SHEIN PC2%</div>
          <div style="font-size:18px;font-weight:600;color:#0C0C0E">{pc2}%</div>
        </td>
        <td width="25%" style="padding:14px 28px;border-right:1px solid #ECEAE5">
          <div style="font-size:9px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#8C8A86;margin-bottom:4px">Webshop Orders</div>
          <div style="font-size:18px;font-weight:600;color:#0C0C0E">{int(web_orders):,}</div>
        </td>
        <td width="25%" style="padding:14px 28px;border-right:1px solid #ECEAE5">
          <div style="font-size:9px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#8C8A86;margin-bottom:4px">Webshop ROAS</div>
          <div style="font-size:18px;font-weight:600;color:#0C0C0E">{str(web_roas)+"x" if web_roas else "-"}</div>
        </td>
        <td width="25%" style="padding:14px 28px">
          <div style="font-size:9px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:#8C8A86;margin-bottom:4px">Avg Hit Rate</div>
          <div style="font-size:18px;font-weight:600;color:#0C0C0E">{str(avg_hr)+"%" if avg_hr else "-"}</div>
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- CTA -->
  <tr><td style="padding:24px 28px;border-top:1px solid #ECEAE5;text-align:center">
    <a href="{DASHBOARD_URL}" style="display:inline-block;background:#1352A2;color:#fff;text-decoration:none;padding:12px 28px;border-radius:6px;font-size:13px;font-weight:500">
      View Full Dashboard &rarr;
    </a>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:14px 28px;background:#F3F2EF;border-top:1px solid #D9D8D2">
    <div style="font-size:10px;color:#8C8A86">Sumwon Studios &nbsp;&middot;&nbsp; Internal use only &nbsp;&middot;&nbsp; Not for external distribution</div>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


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
    meta = {'weeks': d.get('weeks', []), 'updated': d.get('updated', ''), 'hr_wk': d.get('hr_wk', '')}
    return render_template('dashboard.html', meta=meta)


@app.route('/api/data')
def api_data():
    d = load_data()
    if not d:
        return jsonify({'error': 'No data uploaded yet'}), 404
    return jsonify(d)


@app.route('/api/send', methods=['POST'])
def send_email():
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')

    if not smtp_user or not smtp_pass:
        return jsonify({'error': 'Email not configured. Set SMTP_USER and SMTP_PASS in Railway Variables.'}), 500

    data = load_data()
    if not data:
        return jsonify({'error': 'No data to send'}), 400

    body = request.get_json(silent=True) or {}
    week_label = body.get('week_label', data['weeks'][-1] if data.get('weeks') else 'Latest')

    try:
        html_content = build_email_html(data, week_label)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Weekly performance dashboard'
        msg['From']    = smtp_user
        msg['To']      = CEO_EMAIL
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return jsonify({'message': f'Dashboard sent to {CEO_EMAIL}'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    error = None
    success = None

    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd != UPLOAD_PASSWORD:
            error = 'Incorrect password.'
            return render_template('upload.html', error=error, success=None, has_data=data_exists())

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
            return render_template('upload.html', error=error, success=None, has_data=data_exists())

        try:
            new_data = process_files(
                table1_bytes  = files['table1'],
                table2_bytes  = files['table2'],
                cohort_bytes  = files['cohort'],
                webshop_bytes = files['webshop'],
            )

            # Merge with existing so past weeks are never lost
            existing = load_data()
            if existing and existing.get('data'):
                merged = {}
                merged.update(existing['data'])
                merged.update(new_data['data'])
                all_wk_keys = sorted(
                    merged.keys(),
                    key=lambda x: (int(x.split('-')[0]), int(x.split('-W')[1]))
                )
                new_data['data']  = merged
                new_data['weeks'] = all_wk_keys

            save_data(new_data)
            weeks = new_data.get('weeks', [])
            success = f"Dashboard updated. {len(weeks)} weeks loaded ({weeks[0]} to {weeks[-1]})."

        except Exception as e:
            error = f"Processing error: {str(e)}"

    return render_template('upload.html', error=error, success=success, has_data=data_exists())


@app.route('/upload/clear', methods=['POST'])
def clear_data():
    pwd = request.form.get('password', '')
    if pwd != UPLOAD_PASSWORD:
        return redirect(url_for('upload'))
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    return redirect(url_for('upload'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port,
            debug=os.environ.get('DEBUG', 'false').lower() == 'true')
