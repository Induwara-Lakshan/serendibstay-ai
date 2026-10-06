from email import message
import os
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv


load_dotenv()


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_test_email(to_email: str):
    message = EmailMessage()

    message["Subject"] = "SerendibStay AI - Email Test"
    message["From"] = SMTP_EMAIL
    message["To"] = to_email

    message.set_content(
        "Hello!\n\n"
        "This is a test email from SerendibStay AI.\n\n"
        "The email notification system is working successfully."
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()

        server.login(
            SMTP_EMAIL,
            SMTP_PASSWORD
        )

        server.send_message(message)

    return True

def send_provider_request_email(
    to_email: str,
    request_id: int,
    customer_name: str,
    customer_phone: str,
    pickup_location: str,
    destination: str,
    pickup_date,
    pickup_time,
    passengers: int,
    response_token: str,
):
    message = EmailMessage()

    message["Subject"] = f"New Transport Request #{request_id} - SerendibStay AI"
    message["From"] = SMTP_EMAIL
    message["To"] = to_email

    accept_url = (
        f"http://127.0.0.1:8001/transport/respond"
        f"?request_id={request_id}&action=accept&token={response_token}"
    )

    reject_url = (
        f"http://127.0.0.1:8001/transport/respond"
        f"?request_id={request_id}&action=reject&token={response_token}"
    )

    body = f"""
Hello,

You have received a new transport request through SerendibStay AI.

Request ID: {request_id}

Customer: {customer_name}
Customer Phone: {customer_phone}

Pickup Location: {pickup_location}
Destination: {destination}

Pickup Date: {pickup_date}
Pickup Time: {pickup_time}

Passengers: {passengers}

Status: Pending

Please review this transport request.

Accept Request:
{accept_url}

Reject Request:
{reject_url}

SerendibStay AI
"""

    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(message)

    return True

def send_customer_status_email(
    to_email: str,
    customer_name: str,
    request_id: int,
    status: str,
    pickup_location: str,
    destination: str,
    pickup_date,
    pickup_time,
):
    message = EmailMessage()

    message["Subject"] = (
        f"Transport Request #{request_id} {status.title()} - SerendibStay AI"
    )
    message["From"] = SMTP_EMAIL
    message["To"] = to_email

    body = f"""
Hello {customer_name},

Your transport request #{request_id} has been {status} by the transport provider.

Pickup Location: {pickup_location}
Destination: {destination}
Pickup Date: {pickup_date}
Pickup Time: {pickup_time}

Status: {status.title()}

Thank you for using SerendibStay AI.
"""

    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(message)

    return True
