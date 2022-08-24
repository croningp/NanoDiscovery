"""
.. module:: mailer
    :platform: Unix, Windows
    :synopsis: Sends emails to users

.. moduleauthor:: Graham Keenan 2019

"""

import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Outlook server
SERVER = "smtp-mail.outlook.com"
PORT = 587

# Username and password for sender
USERNAME = "croningp_platforms@outlook.com"
PASSWD = "tcgweig2002"


def send_email(system_name: str, toaddr: str, body: str, flag: int = 0):
    """Sends an email to the given address

    Args:
        system_name (str): Name of the system
        toaddr (str): Email address to send mail to
        body (str): Message body
        flag (int, optional): Type of message. Defaults to 0.
    """

    # Create mail, setting To/From
    msg = MIMEMultipart()
    msg["From"] = USERNAME
    msg["To"] = toaddr

    # Set subject based on flag
    if flag == 0:
        msg["Subject"] = f"{system_name} Update"
    elif flag == 1:
        msg["Subject"] = f"CRASH -- {system_name} Error"
    else:
        msg["Subject"] = f"{system_name}"

    # Add the message to the mail
    msg.attach(MIMEText(body, "plain"))

    # Connect to server and send email
    server = smtplib.SMTP(SERVER, PORT)
    server.starttls()
    server.login(USERNAME, PASSWD)
    text = msg.as_string()
    server.sendmail(USERNAME, toaddr, text)
    server.quit()


def notify_all(system_name: str, emails: list, msg: str, flag: int = 0):
    """Sends an email to all given addresses

    Args:
        system_name (str): Name of the system
        emails (list): List of email addresses to mail
        msg (str): Message to send
        flag (int, optional): Flag for type of message. Defaults to 0.
    """

    try:
        # Send main to each address given
        for addr in emails:
            send_email(system_name, addr, msg, flag=flag)

            # Small delay to prevent spam filters from flagging
            time.sleep(1)

    # Most likely raised due to spam
    except Exception as ex:
        # Check if it's a spam exception
        if "Spam" in ex.__str__():
            print("Apparently we're spamming...")
        else:
            print(ex)
