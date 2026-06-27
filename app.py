import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

app = Flask(__name__)

# SMTP Configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

# Admin/Contact Details
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_MOBILE = os.environ.get("ADMIN_MOBILE", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", ADMIN_MOBILE)
TELEGRAM_USERNAME = os.environ.get("TELEGRAM_USERNAME", "Keenlearnerujjwal")

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def get_todays_file():
    today = datetime.now().strftime('%Y_%m_%d')
    return os.path.join(DATA_DIR, f'contacts_{today}.json')

def get_contacts(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_contact(contact_data):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    filepath = get_todays_file()
    contacts = get_contacts(filepath)
    
    contact_data['timestamp'] = datetime.now().isoformat()
    contact_data['processed'] = False
    
    contacts.append(contact_data)
    with open(filepath, 'w') as f:
        json.dump(contacts, f, indent=4)

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        # Only login if credentials are provided
        if SMTP_USER and SMTP_PASS:
            server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        print(f"SMTP Error: {str(e)}")
        return False, str(e)

def get_file_paths():
    today = datetime.now().strftime('%Y_%m_%d')
    base = os.path.join(DATA_DIR, f'contacts_{today}.json')
    failed = os.path.join(DATA_DIR, f'contacts_{today}_failed.json')
    final_failed = os.path.join(DATA_DIR, f'final_failed_contacts_{today}.json')
    return base, failed, final_failed

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json(filepath, data):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def attempt_send_contact(contact, admin_template, user_template):
    """Attempts to send emails for a contact. Returns (success_bool, errors_list)"""
    name = contact.get('name', 'User')
    email = contact.get('email', 'unknown')
    mobile = contact.get('mobile', '')
    business = contact.get('business', '')
    message = contact.get('message', '')

    admin_body = admin_template.format(name=name, email=email, mobile=mobile, business=business, message=message)
    user_body = user_template.format(name=name)

    admin_sent = contact.get('admin_email_sent', False)
    user_sent = contact.get('user_email_sent', False)
    
    errors = []

    # 1. Send Admin Email
    if not admin_sent:
        print(f"Processing Admin Email to {ADMIN_EMAIL}")
        success_admin, err_admin = send_email(ADMIN_EMAIL, f"New Contact: {name}", admin_body)
        if success_admin:
            contact['admin_email_sent'] = True
        else:
            errors.append(f"Admin Email Failed: {err_admin}")

    # 2. Send User Email
    if not user_sent and email and email != 'unknown':
        print(f"Processing User Welcome Email to {email}")
        success_user, err_user = send_email(email, "Welcome to MFD-DOST - We have received your details!", user_body)
        if success_user:
            contact['user_email_sent'] = True
        else:
            errors.append(f"User Email Failed: {err_user}")
    elif email == 'unknown' or not email:
        contact['user_email_sent'] = True

    # 3. Trigger Mock SMS
    if not contact.get('sms_sent', False):
        print(f"[MSG_SERVICE] Sending SMS to ADMIN: {ADMIN_MOBILE}")
        contact['sms_sent'] = True

    success = len(errors) == 0
    if success:
        contact['processed'] = True
    return success, errors

def get_templates():
    base_dir = os.path.dirname(__file__)
    try:
        with open(os.path.join(base_dir, 'templates/admin_notification.txt'), 'r') as f:
            admin_template = f.read()
        with open(os.path.join(base_dir, 'templates/user_welcome.txt'), 'r') as f:
            user_template = f.read()
        return admin_template, user_template
    except Exception as e:
        print(f"Error loading templates: {e}")
        return None, None

def process_new_contacts():
    print(f"[{datetime.now()}] Running 6:00 PM Job: process_new_contacts")
    base_path, failed_path, _ = get_file_paths()
    contacts = load_json(base_path)
    if not contacts:
        return
        
    admin_tpl, user_tpl = get_templates()
    if not admin_tpl: return

    kept_contacts = []
    new_failed_contacts = []
    changes_made = False

    for contact in contacts:
        if contact.get('processed'):
            kept_contacts.append(contact)
            continue
            
        changes_made = True
        success = False
        
        # Try up to 3 times synchronously
        for attempt in range(3):
            success, errors = attempt_send_contact(contact, admin_tpl, user_tpl)
            if success:
                break
                
        if success:
            # attempt starts at 0, so if it succeeds immediately, retry_count is 0
            # attempt 1 -> retry_count 1
            # attempt 2 -> retry_count 2
            contact['retry_count'] = attempt
            kept_contacts.append(contact)
        else:
            # Failed 3 times (attempts 0, 1, 2)
            contact['retry_count'] = 3
            contact['last_error'] = "; ".join(errors)
            new_failed_contacts.append(contact)

    if changes_made:
        save_json(base_path, kept_contacts)
        if new_failed_contacts:
            existing_failed = load_json(failed_path)
            existing_failed.extend(new_failed_contacts)
            save_json(failed_path, existing_failed)
        print(f"[{datetime.now()}] 6:00 PM Job completed. Changes saved.")

def process_failed_contacts():
    print(f"[{datetime.now()}] Running 6:30 PM Job: process_failed_contacts")
    base_path, failed_path, final_failed_path = get_file_paths()
    failed_contacts = load_json(failed_path)
    
    if not failed_contacts:
        return
        
    admin_tpl, user_tpl = get_templates()
    if not admin_tpl: return

    kept_failed_contacts = []
    recovered_contacts = []
    new_final_failed_contacts = []
    changes_made = False

    for contact in failed_contacts:
        if contact.get('processed'):
            recovered_contacts.append(contact)
            changes_made = True
            continue
            
        changes_made = True
        success = False
        
        # Try up to 3 times synchronously
        for attempt in range(3):
            success, errors = attempt_send_contact(contact, admin_tpl, user_tpl)
            if success:
                break
                
        if success:
            # 1st attempt of 2nd job -> 4
            # 2nd attempt of 2nd job -> 5
            # 3rd attempt of 2nd job -> 6
            contact['retry_count'] = 4 + attempt
            recovered_contacts.append(contact)
        else:
            # Failed all 3 times in 2nd job (6 total)
            contact['retry_count'] = 6
            contact['last_error'] = "; ".join(errors)
            new_final_failed_contacts.append(contact)

    if changes_made:
        # Clear out processed/failed contacts from the failed file
        save_json(failed_path, kept_failed_contacts)
        
        if recovered_contacts:
            base_contacts = load_json(base_path)
            base_contacts.extend(recovered_contacts)
            save_json(base_path, base_contacts)
            
        if new_final_failed_contacts:
            final_failed = load_json(final_failed_path)
            final_failed.extend(new_final_failed_contacts)
            save_json(final_failed_path, final_failed)
            
        print(f"[{datetime.now()}] 6:30 PM Job completed. Changes saved.")

# Scheduler setup
scheduler = BackgroundScheduler()
# Run everyday at 18:00 (6:00 PM) for initial processing
scheduler.add_job(func=process_new_contacts, trigger="cron", hour=18, minute=0)
# Run everyday at 18:30 (6:30 PM) to retry failed attempts
scheduler.add_job(func=process_failed_contacts, trigger="cron", hour=18, minute=30)
scheduler.start()

# Flask Routes
@app.route('/')
def index():
    whatsapp_clean = WHATSAPP_NUMBER.replace('+', '').replace(' ', '').replace('-', '')
    telegram_clean = TELEGRAM_USERNAME.replace('@', '')
    telegram_url = telegram_clean if telegram_clean.startswith('http') else 'https://' + telegram_clean
    linkedin_profile = os.environ.get("LINKEDIN_PROFILE", "")
    
    fb_raw = os.environ.get("FACEBOOK_PROFILE", "")
    fb_url = fb_raw if fb_raw.startswith('http') else f"https://www.facebook.com/{fb_raw}" if fb_raw else ""
    
    ig_raw = os.environ.get("INSTAGRAM_PROFILE", "")
    ig_url = ig_raw if ig_raw.startswith('http') else f"https://www.instagram.com/{ig_raw}" if ig_raw else ""

    app_email = os.environ.get("APP_EMAIL", ADMIN_EMAIL)

    return render_template('index.html', 
                           whatsapp_number=whatsapp_clean, 
                           telegram_url=telegram_url, 
                           linkedin_profile=linkedin_profile, 
                           facebook_url=fb_url,
                           instagram_url=ig_url,
                           app_email=app_email)

@app.route('/api/contact', methods=['POST'])
def contact():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    if not data or not data.get('name') or not data.get('email'):
        return jsonify({"success": False, "message": "Name and Email are required."}), 400

    # Save to JSON
    save_contact(data)
    
    return jsonify({"success": True, "message": "Your message has been received."}), 200

@app.route('/api/trigger-batch', methods=['GET', 'POST'])
def trigger_batch():
    # Only allow trigger if a matching token is provided, protecting the deployed app
    token = request.args.get('token')
    
    # Strictly require a token from the environment (.env or Heroku Config Vars)
    expected_token = os.environ.get("ADMIN_TOKEN")
    
    # Block access if no token is configured in the environment or if it doesn't match
    if not expected_token or token != expected_token:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    # Manual bypass to immediately process pending contacts
    process_new_contacts() # Run the 6 PM daily job logic
    process_failed_contacts()  # Run the 6:30 PM retry job logic
    return jsonify({"success": True, "message": "Batch processes triggered manually. Check terminal logs."}), 200

if __name__ == '__main__':
    # When running with debug=True, the scheduler might start twice due to the reloader.
    app.run(host='0.0.0.0', debug=True, port=8000, use_reloader=False)
