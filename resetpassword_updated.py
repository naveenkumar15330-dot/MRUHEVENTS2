from flask import Blueprint, render_template, request, jsonify, session
from pymongo import MongoClient
from email.message import EmailMessage
import smtplib
import random
import bcrypt
from datetime import datetime, timedelta

reset_bp = Blueprint('reset_bp', __name__)

mongo_client = MongoClient("mongodb+srv://naveen_03:Navi630599@cluster0.b2w86jh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
mongo_db = mongo_client["studentinformation"]
user_data_collection = mongo_db["student"]

SENDER_EMAIL = "mruhevents@gmail.com"
SENDER_APP_PASSWORD = "zwvkhdsatclxqjtx"

@reset_bp.route('/reset_password')
def display_reset_page():
    return render_template("resetpassword.html")

@reset_bp.route("/send_otp1", methods=["POST"])
def send_otp1():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "Email is required."})

    user = user_data_collection.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "message": "❌ Email not found in our records."})

    last_otp_time = session.get("otp_time")
    now = datetime.now()
    if last_otp_time:
        elapsed = now - datetime.strptime(last_otp_time, "%Y-%m-%d %H:%M:%S")
        if elapsed.total_seconds() < 180:
            return jsonify({"success": False, "message": "⏳ Please wait before requesting another OTP."})

    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    session["otp"] = otp
    session["otp_email"] = email
    session["otp_time"] = now.strftime("%Y-%m-%d %H:%M:%S")

    try:
        msg = EmailMessage()
        msg.set_content(f"Your OTP for password reset is: {otp}")
        msg["Subject"] = "Your OTP - MRU Password Reset"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp.send_message(msg)

        return jsonify({"success": True, "message": "✅ OTP sent successfully to your email."})

    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Failed to send email: {str(e)}"})

@reset_bp.route('/reset_password', methods=['POST'])
def update_user_password():
    data = request.get_json()
    user_otp = data.get("otp")
    new_pass = data.get("password")
    confirm_pass = data.get("confirmPassword")

    saved_otp = session.get("otp")
    saved_email = session.get("otp_email")

    if not saved_email:
        return jsonify(success=False, message="⚠️ Session expired. Please request a new OTP.")

    if user_otp != saved_otp:
        return jsonify(success=False, message="❌ Invalid OTP entered.")

    if new_pass != confirm_pass:
        return jsonify(success=False, message="❌ Passwords do not match.")

    # Hash new password
    hashed_new_password = bcrypt.hashpw(new_pass.encode("utf-8"), bcrypt.gensalt())

# Update password in DB
    user_data_collection.update_one(
    {"email": saved_email},
    {"$set": {"password": hashed_new_password.decode('utf-8')}}
)


    session.pop("otp", None)
    session.pop("otp_email", None)
    session.pop("otp_time", None)

    return jsonify(success=True, message="✅ Your password has been reset successfully.")
    
