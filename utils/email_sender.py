import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import BytesIO
import logging
from typing import Optional

def send_email(recipient_email: str, subject: str, body: str, attachment: Optional[BytesIO] = None) -> bool:
    """
    Send an email with optional PDF attachment
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject
        body: Email body text
        attachment: BytesIO object containing PDF data (optional)
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Get email credentials from environment variables
        sender_email = os.getenv("EMAIL_ADDRESS", "info@theaiconsultant.co.uk")
        sender_password = os.getenv("EMAIL_PASSWORD", "")
        
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        
        # Attach text body
        message.attach(MIMEText(body, "plain"))
        
        # Attach PDF if provided
        if attachment:
            attachment_part = MIMEApplication(attachment.getvalue(), Name="ai_image_ideas.pdf")
            attachment_part["Content-Disposition"] = 'attachment; filename="ai_image_ideas.pdf"'
            message.attach(attachment_part)
        
        # Connect to SMTP server and send email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        logging.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        return False
