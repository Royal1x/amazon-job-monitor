"""Send a simple Twilio test alert without changing the live job monitor."""

import argparse
import os
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from twilio.rest import Client


JOB_SEARCH_PAGE_URL = "https://hiring.amazon.com/app#/jobSearch"

REQUIRED_ENV_VARS = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_WHATSAPP_FROM",
    "ALERT_TO_WHATSAPP",
)

CALL_ENV_VARS = (
    "TWILIO_FROM_PHONE",
    "ALERT_TO_PHONE",
)


def parse_args() -> argparse.Namespace:
    """Read easy command-line options for a beginner-friendly test alert."""
    parser = argparse.ArgumentParser(
        description="Send a test Amazon job alert through Twilio.",
    )
    parser.add_argument(
        "--city",
        default="Rochester",
        help="City name to include in the test alert.",
    )
    parser.add_argument(
        "--state",
        default="NY",
        help="State name to include in the test alert.",
    )
    parser.add_argument(
        "--title",
        default="Sample Warehouse Associate",
        help="Job title to include in the test alert.",
    )
    parser.add_argument(
        "--link",
        default=JOB_SEARCH_PAGE_URL,
        help="Link to include in the test alert.",
    )
    parser.add_argument(
        "--with-call",
        action="store_true",
        help="Also place a phone call after sending the WhatsApp test message.",
    )
    return parser.parse_args()


def load_settings(with_call: bool) -> dict[str, str] | None:
    """Load Twilio settings and return None with a helpful message if missing."""
    load_dotenv()

    required_names = list(REQUIRED_ENV_VARS)
    if with_call:
        required_names.extend(CALL_ENV_VARS)

    settings = {name: os.getenv(name, "").strip() for name in required_names}
    missing = [name for name, value in settings.items() if not value]
    if missing:
        print("The test alert could not run because some settings are missing.")
        print("Add these values to your .env file first:")
        for name in missing:
            print(f"- {name}")
        return None

    return settings


def build_test_message(title: str, city: str, state: str, link: str) -> str:
    """Create a clear test message so it is not confused with a real opening."""
    return (
        f"TEST ALERT: Amazon warehouse job found: {title} in {city}, {state}. "
        f"Apply here: {link}"
    )


def split_recipients(raw_value: str) -> list[str]:
    """Split a comma-separated recipient list into clean values."""
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def main() -> None:
    """Send a WhatsApp test alert, with an optional phone call."""
    args = parse_args()
    settings = load_settings(with_call=args.with_call)
    if not settings:
        return

    client = Client(
        settings["TWILIO_ACCOUNT_SID"],
        settings["TWILIO_AUTH_TOKEN"],
    )

    message_text = build_test_message(
        title=args.title,
        city=args.city,
        state=args.state,
        link=args.link,
    )

    for whatsapp_recipient in split_recipients(settings["ALERT_TO_WHATSAPP"]):
        whatsapp_message = client.messages.create(
            body=message_text,
            from_=settings["TWILIO_WHATSAPP_FROM"],
            to=whatsapp_recipient,
        )
        print(f"WHATSAPP SID for {whatsapp_recipient}: {whatsapp_message.sid}")

    if args.with_call:
        for phone_recipient in split_recipients(settings["ALERT_TO_PHONE"]):
            call = client.calls.create(
                twiml=f"<Response><Say>{escape(message_text)}</Say></Response>",
                from_=settings["TWILIO_FROM_PHONE"],
                to=phone_recipient,
            )
            print(f"CALL SID for {phone_recipient}: {call.sid}")


if __name__ == "__main__":
    main()
