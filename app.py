from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import requests
import os
import datetime

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'frontend_secret_key')
API_URL = os.getenv("API_URL", "http://backend:5000")

# Database Configuration for Session Storage
# User requested "save session login to database"
# We default to filesystem if no DB URI provided, but recommend DB for production/persistence
db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')

if not db_uri and os.getenv('POSTGRES_DB'):
    # Construct URI from individual vars
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT')
    dbname = os.getenv('POSTGRES_DB')
    db_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

if db_uri:
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    app.config['SESSION_SQLALCHEMY'] = db
    
    # Create session table
    with app.app_context():
        try:
            db.create_all()
        except:
            pass # DB might not be ready or table exists
    
    # Initialize Flask-Session only if we are using server-side storage (DB)
    Session(app)

# If no DB configured, we do NOT initialize Flask-Session.
# Flask will automatically use its default Client-Side Secure Cookie Session.
# This ensures the application remains stateless (state in cookie).

def get_api_url(path):
    return f"{API_URL.rstrip('/')}{path}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            response = requests.post(get_api_url("/auth/login"), json={
                "username": username,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                session['token'] = data['token']
                # Session is automatically saved to DB/Filesystem by Flask-Session
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            flash(f'Connection error: {str(e)}', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    token = session.get('token')
    if not token:
        return redirect(url_for('login'))
        
    page = request.args.get('page', 1, type=int)
    limit = 5
    search = request.args.get('search', '')
    
    start = (page - 1) * limit
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "draw": 1,
        "start": start,
        "length": limit,
        "search[value]": search
    }
    
    try:
        response = requests.get(get_api_url("/api/ktp"), headers=headers, params=params)
        
        if response.status_code == 401:
            session.clear()
            return redirect(url_for('login'))
            
        if response.status_code == 200:
            data = response.json()
            records = data.get('data', [])
            total_records = data.get('recordsFiltered', 0)
            total_pages = (total_records + limit - 1) // limit
            
            return render_template('dashboard.html', 
                                   records=records, 
                                   page=page, 
                                   total_pages=total_pages, 
                                   total_records=total_records,
                                   start=start,
                                   search=search)
        else:
            flash('Failed to fetch data', 'warning')
            return render_template('dashboard.html', records=[], page=1, total_pages=0, start=0, search=search, total_records=0)
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('dashboard.html', records=[], page=1, total_pages=0, start=0, search=search, total_records=0)

@app.route('/ktp/upload', methods=['GET', 'POST'])
def upload_ktp():
    token = session.get('token')
    if not token:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file:
            headers = {"Authorization": f"Bearer {token}"}
            # Prepare file for upload to backend
            files = {'file': (file.filename, file.stream, file.mimetype)}
            
            try:
                # Call Backend Agent
                response = requests.post(get_api_url("/api/ocr/extract"), headers=headers, files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    extracted_data = result.get('data', {})
                    
                    # Store extracted data in session to pre-fill the Add Form
                    session['ocr_data'] = extracted_data
                    flash('KTP Scanned Successfully! Please review the data.', 'success')
                    return redirect(url_for('add_ktp'))
                else:
                    msg = response.json().get('message', 'Unknown error')
                    flash(f"OCR Failed: {msg}", 'danger')
            except Exception as e:
                flash(f"Connection Error: {str(e)}", 'danger')

    return render_template('upload.html')
    
@app.route('/ktp/add', methods=['GET', 'POST'])
def add_ktp():
    token = session.get('token')
    if not token:
        return redirect(url_for('login'))

    prefill_data = session.pop('ocr_data', None)
        
    if request.method == 'POST':
        data = {
            "nik": request.form.get('nik'),
            "full_name": request.form.get('full_name'),
            "birth_place": request.form.get('birth_place'),
            "birth_date": request.form.get('birth_date'),
            "gender": request.form.get('gender'),
            "blood_type": request.form.get('blood_type'),
            "address": request.form.get('address'),
            "rt_rw": request.form.get('rt_rw'),
            "village_kelurahan": request.form.get('village_kelurahan'),
            "district_kecamatan": request.form.get('district_kecamatan'),
            "religion": request.form.get('religion'),
            "marital_status": request.form.get('marital_status'),
            "occupation": request.form.get('occupation'),
            "citizenship": request.form.get('citizenship'),
            "expiry_date": request.form.get('expiry_date'),
            "registration_date": request.form.get('registration_date')
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.post(get_api_url("/api/ktp"), headers=headers, json=data)
            if response.status_code in [200, 201]:
                flash('Record created successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                msg = response.json().get('message', 'Failed to create record')
                flash(f'Error: {msg}', 'danger')
                return render_template('form.html', ktp=data) 
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return render_template('form.html', ktp=data)
            
    return render_template('form.html', ktp=prefill_data)

@app.route('/ktp/edit/<nik>', methods=['GET', 'POST'])
def edit_ktp(nik):
    token = session.get('token')
    if not token:
        return redirect(url_for('login'))
        
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == 'POST':
        data = {
            # NIK cannot be changed usually, but form sends it. We use URL param for ID.
            "full_name": request.form.get('full_name'),
            "birth_place": request.form.get('birth_place'),
            "birth_date": request.form.get('birth_date'),
            "gender": request.form.get('gender'),
            "blood_type": request.form.get('blood_type'),
            "address": request.form.get('address'),
            "rt_rw": request.form.get('rt_rw'),
            "village_kelurahan": request.form.get('village_kelurahan'),
            "district_kecamatan": request.form.get('district_kecamatan'),
            "religion": request.form.get('religion'),
            "marital_status": request.form.get('marital_status'),
            "occupation": request.form.get('occupation'),
            "citizenship": request.form.get('citizenship'),
            "expiry_date": request.form.get('expiry_date'),
            "registration_date": request.form.get('registration_date')
        }
        
        try:
            response = requests.put(get_api_url(f"/api/ktp/{nik}"), headers=headers, json=data)
            if response.status_code == 200:
                flash('Record updated successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                msg = response.json().get('message', 'Failed to update record')
                flash(f'Error: {msg}', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            
    # GET - Fetch record to fill form
    try:
        # We need an endpoint to get ONE record. Backend has /api/ktp/<nik>
        response = requests.get(get_api_url(f"/api/ktp/{nik}"), headers=headers)
        if response.status_code == 200:
            ktp = response.json().get('ktp_record')
            return render_template('form.html', ktp=ktp)
        else:
            flash('Record not found', 'danger')
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/ktp/delete/<nik>', methods=['POST'])
def delete_ktp(nik):
    token = session.get('token')
    if not token:
        return redirect(url_for('login'))
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(get_api_url(f"/api/ktp/{nik}"), headers=headers)
        if response.status_code == 200:
            flash('Record deleted successfully!', 'success')
        else:
            flash('Failed to delete record', 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard'))

if __name__ == '__main__':  
    app.run(host='0.0.0.0', port=80, debug=True)
