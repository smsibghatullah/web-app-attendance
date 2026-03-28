from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import json
import os
from dotenv import load_dotenv
import urllib
from datetime import datetime

load_dotenv()

app = Flask(__name__)

BASE_URL = os.getenv('BASE_URL')
DB_NAME = os.getenv('DB_NAME')
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret')

@app.route('/')
def home():
    if 'token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_email = request.form['email']
        password = request.form['password']

        headers = {'Content-Type': 'application/json'}

        url1 = f"{BASE_URL}/web/session/authenticate"
        print(url1,"=========================")
        payload1 = {
            "jsonrpc": "2.0",
            "params": {
                "db": DB_NAME,
                "login": login_email,
                "password": password,
            }
        }

        s = requests.Session()
        response1 = s.post(url1, headers=headers, json=payload1)

        if response1.status_code != 200:
            flash("Error contacting Odoo", "error")
            return render_template('login.html')

        data1 = response1.json()
        print("🟢 Session Response:", data1)

        session_cookie = s.cookies.get('session_id')
        print("🍪 Session ID:", session_cookie)

        if not session_cookie:
            flash("Failed to get session cookie", "error")
            return render_template('login.html')

        url2 = f"{BASE_URL}/api1/auth/token"
        payload2 = {
            "db": DB_NAME,
            "login": login_email,
            "password": password
        }

        headers2 = {
            'Content-Type': 'application/json',
            'Cookie': f'session_id={session_cookie}'
        }

        response2 = requests.post(url2, headers=headers2, data=json.dumps(payload2))
        print("🔹 Token Response:", response2.text)

        if response2.status_code != 200:
            flash("Token request failed", "error")
            return render_template('login.html')

        data2 = response2.json()
        result = data2.get("result")

        if isinstance(result, dict) and result.get("uid"):
            session['uid'] = result.get("uid")
            session['token'] = result.get("access_token")
            session['email'] = result.get("user_email")
            session['name'] = result.get("user_name")
            session['employee_id'] = result.get("hr_employee_id")
            session['partner_id'] = result.get("partner_id")
            session['access_token'] = result.get('access_token')
            session['session_id'] = session_cookie

            print("✅ Login successful, redirecting to dashboard...")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "error")

    return render_template('login.html')

@app.route('/get_user_attendance', methods=['GET'])
def get_user_attendance():
    """Fetch all attendance records for the logged-in user from Odoo."""
    if 'access_token' not in session or 'employee_id' not in session:
        return redirect(url_for('login'))

    headers = {
        'access-token': session['access_token']
    }

    employee_id = session['employee_id']
    print(employee_id,"employee_id")
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    domain = str([["employee_id", "=", employee_id]])


    url = f"{BASE_URL}/api/hr.attendance?domain={domain}"
    print(url,"===========",headers)

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Error fetching attendance:", response.text)
        return {"success": False, "message": "Failed to fetch attendance"}, 400

    data = response.json()
    print(data,"====================================")
    records = data.get("data", [])

    attendance_today = any(
        rec.get("check_in") and today_str in rec.get("check_in")
        for rec in records
    )

    return {
        "success": True,
        "attendance_today": attendance_today,
        "records": records
    }


@app.route('/submit_timesheet', methods=['POST'])
def submit_timesheet():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    data = request.json
    headers = {
        'Content-Type': 'application/json',
        'access-token': session['access_token']
    }

    payload = {
        "employee_id": session['employee_id'],
        "check_in": data['time_in'],      # already formatted as 'YYYY-MM-DD HH:mm:ss'
        "check_out": data['time_out'],
        "break_time": str(data['break_time']),
        "date_time": data['date'],
        "comment": data['comment'],
    }

    print("🟢 Sending to Odoo:", payload)
    res = requests.post(f"{BASE_URL}/api/hr.attendance",
                        json=payload, headers=headers)

    print("✅ Odoo Response:", res.text)

    if res.status_code == 200:
        return {"success": True, "message": "Timesheet Submitted"}
    else:
        return {"success": False, "message": "Failed to submit"}, 400




@app.route('/dashboard')
def dashboard():
    if 'token' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', employee_name=session['name'], email=session.get('email'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5040, debug=True)
