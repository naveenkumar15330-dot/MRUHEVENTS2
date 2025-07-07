# payment_module.py

from flask import Blueprint, render_template, request, send_file
from pymongo import MongoClient
from datetime import datetime
from io import BytesIO
import pyqrcode
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
import os

payment_bp = Blueprint('payment_bp', __name__)

# Constants
ORG_NAME = "MRUH-EVENTS"
SENDER_EMAIL = "naveenkumar15330@gmail.com"
SENDER_PASSWORD = "opnatolaqxlmetqs"
UPI_ID = "6305996729-2@ybl"

client = MongoClient("mongodb+srv://naveen_03:Navi630599@cluster0.b2w86jh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
event_collection = client["eventregistration"]["events"]
student_db = client["StudentData"]
receipt_collection = student_db["Receipts"]
information = client["studentinformation"]
information_collection = information["student"]

@payment_bp.route('/payment')
def payment():
    events = list(event_collection.find({}, {"_id": 0}))
    return render_template("payment.html", events=events)

@payment_bp.route('/receipt')
def receipt():
    return render_template('receipt.html')

@payment_bp.route('/generate_qr', methods=["POST"])
def generate_qr():
    event_name = request.form.get("event")
    amountPaid = request.form.get("amountPaid")
    email = request.form.get("email", "").strip().lower()
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    if not all([event_name, amountPaid, email]):
        return "Missing required fields (event, amount, email)", 400

    student = information_collection.find_one({"email": email})
    if not student:
        return f"Email {email} not registered", 403

    name = student.get("name", "N/A")
    rollno = student.get("rollno", "N/A")
    year = student.get("year", "N/A")
    branch = student.get("branch", "N/A")

    upi_link = f"upi://pay?pa={UPI_ID}&pn={ORG_NAME}&am={amountPaid}&cu=INR&tn=Payment for {event_name}"
    qr = pyqrcode.create(upi_link)
    qr_file_path = "temp_qr.png"
    qr.png(qr_file_path, scale=6)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Event Payment Receipt", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Name: {name}", ln=True)
    pdf.cell(200, 10, f"Roll No: {rollno}", ln=True)
    pdf.cell(200, 10, f"Year: {year}", ln=True)
    pdf.cell(200, 10, f"Branch: {branch}", ln=True)
    pdf.cell(200, 10, f"Event: {event_name}", ln=True)
    pdf.cell(200, 10, f"Amount: Rs. {amountPaid}", ln=True)
    pdf.cell(200, 10, f"Date: {timestamp}", ln=True)
    pdf.cell(200, 10, f"UPI ID: {UPI_ID}", ln=True)
    pdf.cell(200, 10, "Scan this QR to pay:", ln=True)
    pdf.image(qr_file_path, x=60, y=120, w=90)

    pdf_buffer = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_buffer.write(pdf_bytes)
    pdf_buffer.seek(0)

    receipt_collection.insert_one({
        "name": name,
        "rollno": rollno,
        "year": year,
        "branch": branch,
        "event": event_name,
        "amount": amountPaid,
        "email": email,
        "timestamp": timestamp,
        "upi_id": UPI_ID
    })

    try:
        msg = EmailMessage()
        msg["Subject"] = "Your Event Payment Receipt"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        msg.set_content(f"""
Hello {name},

Thank you for registering for {event_name}.
Attached is your payment receipt.

- {ORG_NAME}
        """)

        msg.add_attachment(pdf_buffer.read(), maintype="application", subtype="pdf", filename="receipt.pdf")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print("✅ Email sent successfully")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")

    if os.path.exists(qr_file_path):
        os.remove(qr_file_path)

    pdf_buffer.seek(0)
    return send_file(pdf_buffer, as_attachment=True, download_name="receipt.pdf", mimetype="application/pdf")
