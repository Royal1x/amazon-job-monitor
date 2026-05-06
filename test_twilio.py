"""Send a simple Twilio test alert without changing the live job monitor."""

import argparse
import os
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from twilio.rest import Client


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
        default="https://hiring.amazon.com/",
        help="Link to include in the test alert.",
    )
    parser.add_argument(
        "--with-call",
        action="store_true",
        help="Also place a phone call after sending the WhatsApp test message.",
    )
    return parser.parse_args()


def build_test_message(title: str, city: str, state: str, link: str) -> str:
    """Create a clear test message so it is not confused with a real opening."""
    return (
        f"TEST ALERT: Amazon warehouse job found: {title} in {city}, {state}. "
        f"Apply here: {link}"
    )


def main() -> None:
    """Send a WhatsApp test alert, with an optional phone call."""
    args = parse_args()
    load_dotenv()

    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )

    message_text = build_test_message(
        title=args.title,
        city=args.city,
        state=args.state,
        link=args.link,
    )

    whatsapp_message = client.messages.create(
        body=message_text,
        from_=os.environ["TWILIO_WHATSAPP_FROM"],
        to=os.environ["ALERT_TO_WHATSAPP"],
    )

    print(f"WHATSAPP SID: {whatsapp_message.sid}")

    if args.with_call:
        call = client.calls.create(
            twiml=f"<Response><Say>{escape(message_text)}</Say></Response>",
            from_=os.environ["TWILIO_FROM_PHONE"],
            to=os.environ["ALERT_TO_PHONE"],
        )
        print(f"CALL SID: {call.sid}")


if __name__ == "__main__":
    main()
