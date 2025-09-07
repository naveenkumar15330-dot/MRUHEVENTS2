import email
from flask import Flask, render_template, request, session, jsonify, url_for,redirect
from pymongo import MongoClient
from email.message import EmailMessage
from datetime import datetime, timedelta
import smtplib
import random,re
import bcrypt
from flask import flash
app = Flask(__name__)
from resetpassword_updated import reset_bp
from payment import payment_bp
app.register_blueprint(reset_bp)
app.register_blueprint(payment_bp)

app.secret_key = "naveenkumar"
app.permanent_session_lifetime = timedelta(minutes=5)
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
# MongoDB connection
client = MongoClient("mongodb+srv://naveen_03:Navi630599@cluster0.b2w86jh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["studentinformation"]
collection = db["student"]
resetpassword=db["student"]
db = client["eventregistration"]           
dbcf= client['feedback']
feedback_collection =dbcf['contactform']
dbpl = client["eventregistration"]
events_collectionpl = dbpl["events"]
db1 = client["student"]
collection1 = db1["studentinformation"] 
user_collection1 = db1["studentinformation"] 
dbpp = client["student"]
collectionpp = dbpp["studentinformation"]
# Email configuration
SENDER_EMAIL = "mruhevents@gmail.com"
SENDER_PASSWORD = "zwvkhdsatclxqjtx"  # Gmail App Password
#login route

@app.route("/")
def index():
    return render_template("login.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = collection.find_one({"email": email})

        if user:
            stored_hash = user['password'].encode('utf-8')  # stored as bcrypt string
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                session['user'] = email
                flash('✅ Login successful', 'success')
                return redirect(url_for('home'))
            else:
                flash('❌ Incorrect password.', 'error')
        else:
            flash('❌ Email not found.', 'error')
        return redirect(url_for('login'))

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))
# OTP Sending Route
@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"message": "❌ Email is required."}), 400

    # Check if email already exists
    if collection.find_one({"email": email}):
        return jsonify({"message": "❌ Email already registered."}), 409

    now = datetime.now()

    # Check for 2-minute cooldown
    last_sent_time = session.get("last_otp_time")
    if last_sent_time:
        elapsed = now - datetime.strptime(last_sent_time, "%Y-%m-%d %H:%M:%S")
        if elapsed.total_seconds() < 120:
            remaining = 120 - int(elapsed.total_seconds())
            return jsonify({"message": f"⏳ Wait {remaining} seconds before resending OTP."}), 429

    # Generate OTP and store in session
    otp = str(random.randint(100000, 999999))
    session["otp"] = otp
    session["otp_email"] = email
    session["last_otp_time"] = now.strftime("%Y-%m-%d %H:%M:%S")

    # Send email
    try:
        msg = EmailMessage()
        msg["Subject"] = "Your OTP for Event Registration"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        msg.set_content(f"Your OTP is: {otp}")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)

        return jsonify({"message": "✅ OTP sent successfully!"})
    except Exception as e:
        print("Email sending error:", e)
        return jsonify({"message": "❌ Failed to send OTP."}), 500

# Registration route
@app.route("/login1", methods=["POST"])
def login1():  # ✅ Function name matches the endpoint now
    name = request.form.get("name")
    rollno = request.form.get("rollno")
    email = request.form.get("email")
    entered_otp = request.form.get("otp")
    year = request.form.get("year")
    branch = request.form.get("branch")
    password = request.form.get("password")
    re_password = request.form.get("re_password")

    # OTP validation
    if entered_otp != session.get("otp") or email != session.get("otp_email"):
        return "❌ Incorrect OTP or mismatched email.", 400

    # Password match check
    if password != re_password:
        return "❌ Passwords do not match.", 400

    # Prevent duplicate registration
    if collection.find_one({"email": email}):
        return "❌ Email already exists. Please login instead.", 409

    # Hash password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Store user data
    user_data = {
    "name": name,
    "rollno": rollno,
    "email": email,
    "year": year,
    "branch": branch,
    "password": hashed.decode('utf-8')  # Store as string
}

    collection.insert_one(user_data)
    return render_template('login.html')
#reset password route

# Serve registration form
@app.route("/register")
def register():
    return render_template("register.html")

# Terms route
@app.route("/terms")
def terms():
    return render_template("T&C.html")
######################################
#main page route
@app.route('/home')
def home():
    return render_template("main.html")
@app.route('/eventregistration')
def eventregistration():
    return render_template('eventregistration.html') 
TIME_GAP = timedelta(minutes=5) # HTML file should be inside `templates/`
@app.route('/register2', methods=['POST'])
def register2():
    data = request.get_json()
    rollno = data.get("rollno")

    if not rollno:
        return jsonify({'success': False, 'message': 'Missing roll number'}), 400

    now = datetime.now()

    # Check last submission for same roll number
    last_submission = collection.find_one({"rollno": rollno}, sort=[("submitted_at", -1)])
    if last_submission and "submitted_at" in last_submission:
        if now - last_submission["submitted_at"] < TIME_GAP:
            wait_time = TIME_GAP - (now - last_submission["submitted_at"])
            return jsonify({
                'success': False,
                'message': f"Please wait {int(wait_time.total_seconds() // 60)} minute(s) before submitting again."
            }), 429

    try:
        # Parse and validate fields
        data['date'] = datetime.strptime(data['date'], "%Y-%m-%d")
        data['amountPaid'] = int(data['amountPaid'])
        data['submitted_at'] = now

        events_collectionpl.insert_one(data)
        return jsonify({'success': True, 'message': 'Registration successful'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/contact')
def contact():
    return render_template("contactus.html") 


@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    try:
        # Get form data
        name = request.form.get("name")
        email = request.form.get("email")
        rollno = request.form.get("rollno")
        subject = request.form.get("subject")
        message = request.form.get("message")

        # Insert into MongoDB
        contact_data = {
            "name": name,
            "email": email,
            "rollno": rollno,
            "subject": subject,
            "message": message,
            "submitted_at": datetime.now()  # Timestamp
        }

        feedback_collection.insert_one(contact_data)

        return jsonify({"message": "Your message has been received. Thank you!"}), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route('/profile')
def profile():
    return render_template('profile.html')
@app.route('/get-profile', methods=['POST'])
def get_profile():
    email = request.json.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    student = collection.find_one({'email': email})
    if student:
        return jsonify({
            'name': student.get('name', 'Unknown'),
            'student_id': student.get('rollno', 'N/A'),
            'email': student.get('email'),
            'department': student.get('branch', 'N/A'),
            'year': student.get('year', 'N/A'),
        })
    else:
        return jsonify({'error': 'Profile not found'}), 404

@app.route('/participants')
def participants():
    return render_template('participantList.html')

@app.route('/api/participants')
def get_participants():
    try:
        # Fetch all events and convert to list
        participants = list(events_collectionpl.find({}))
        # Convert ObjectId to string for JSON serialization
        for participant in participants:
            participant['_id'] = str(participant['_id'])
        return jsonify(participants)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/about')
def about():
    return render_template('aboutus.html')

@app.route('/announcements')
def announcements():
    return render_template('annoucements.html')


def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def generate_otp():
    return "".join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp_email(to_email, otp):
    from_mail = "mruhevents@gmail.com"
    app_password = "zwvkhdsatclxqjtx"  # App password only

    if not is_valid_email(to_email):
        return False, "Invalid email format"

    try:
        msg = EmailMessage()
        msg["Subject"] = "OTP Verification"
        msg["From"] = from_mail
        msg["To"] = to_email
        msg.set_content(f"Your OTP is: {otp}")

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_mail, app_password)
        server.send_message(msg)
        server.quit()
        return True, "OTP sent successfully"
    except Exception as e:
        return False, str(e)
#############################################################################################################
if __name__ == '__main__':
    app.run(debug=True)
