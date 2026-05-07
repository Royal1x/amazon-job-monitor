"""
Amazon warehouse job monitor for Liverpool and East Syracuse, New York.

This beginner-friendly script:
1. Checks Amazon's hourly hiring site every few seconds.
2. Looks for warehouse jobs in Liverpool, NY and East Syracuse, NY.
3. Sends a WhatsApp message and an automated phone call for brand-new jobs.
4. Saves seen job IDs so the same job is not announced twice.
"""

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import urljoin
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from twilio.rest import Client


# This is the official Amazon page people use in the browser.
# It is a JavaScript app, so requests + BeautifulSoup cannot directly scrape
# the visible job list from that exact page.
JOB_SEARCH_PAGE_URL = "https://hiring.amazon.com/app#/jobSearch"

# This Amazon page contains HTML that requests + BeautifulSoup can read.
SEARCH_URL = "https://hiring.amazon.com/search/warehouse-jobs"

# Keep the request timeout in one place so it is easy to adjust later.
REQUEST_TIMEOUT_SECONDS = 15

# We only want jobs in these locations.
TARGET_LOCATIONS = (
    ("Liverpool", "NY"),
    ("East Syracuse", "NY"),
)

# This file stores job IDs we have already seen.
SEEN_JOBS_FILE = Path(__file__).with_name("seen_jobs.json")

# These environment variables are used for Twilio.
TWILIO_ACCOUNT_SID_ENV = "TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN_ENV = "TWILIO_AUTH_TOKEN"
TWILIO_FROM_PHONE_ENV = "TWILIO_FROM_PHONE"
ALERT_TO_PHONE_ENV = "ALERT_TO_PHONE"
TWILIO_WHATSAPP_FROM_ENV = "TWILIO_WHATSAPP_FROM"
ALERT_TO_WHATSAPP_ENV = "ALERT_TO_WHATSAPP"

# This environment variable lets us change how often the script checks.
CHECK_INTERVAL_SECONDS_ENV = "CHECK_INTERVAL_SECONDS"
DEFAULT_CHECK_INTERVAL_SECONDS = 1
SYRACUSE_TIMEZONE = ZoneInfo("America/New_York")

# Turn these on or off if you only want one alert type later.
SEND_WHATSAPP_ALERTS = True
SEND_CALL_ALERTS = True

# A browser-like User-Agent helps websites return normal HTML.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# These keywords help us stay focused on warehouse-style roles.
WAREHOUSE_KEYWORDS = (
    "warehouse",
    "fulfillment",
    "sortation",
    "distribution",
    "delivery station",
    "amazon air",
    "locker+",
)

# These are generic buttons or links, not real job titles.
GENERIC_LINK_TEXT = {
    "",
    "apply",
    "apply now",
    "join our team",
    "search jobs",
    "search jobs near you",
    "search warehouse jobs",
    "view all syracuse area jobs",
}

# Load values from a local .env file if it exists.
load_dotenv()


def load_check_interval_seconds() -> int:
    """
    Read the check interval from the environment.

    If the value is missing or invalid, fall back to the beginner-friendly
    default of 1 second.
    """
    raw_value = os.getenv(
        CHECK_INTERVAL_SECONDS_ENV,
        str(DEFAULT_CHECK_INTERVAL_SECONDS),
    ).strip()

    try:
        interval = int(raw_value)
    except ValueError:
        print(
            f"Invalid {CHECK_INTERVAL_SECONDS_ENV} value {raw_value!r}. "
            f"Using {DEFAULT_CHECK_INTERVAL_SECONDS} second(s) instead."
        )
        return DEFAULT_CHECK_INTERVAL_SECONDS

    if interval < 1:
        print(
            f"{CHECK_INTERVAL_SECONDS_ENV} must be 1 or higher. "
            f"Using {DEFAULT_CHECK_INTERVAL_SECONDS} second(s) instead."
        )
        return DEFAULT_CHECK_INTERVAL_SECONDS

    return interval


# The user originally asked for a check every second, so that stays the default.
CHECK_INTERVAL_SECONDS = load_check_interval_seconds()


def load_seen_jobs() -> Set[str]:
    """Load saved job IDs from disk. Return an empty set if the file is missing."""
    if not SEEN_JOBS_FILE.exists():
        return set()

    try:
        with SEEN_JOBS_FILE.open("r", encoding="utf-8") as file:
            saved_ids = json.load(file)
        return set(saved_ids)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read {SEEN_JOBS_FILE.name}: {error}")
        return set()


def save_seen_jobs(seen_jobs: Set[str]) -> None:
    """Save the seen job IDs so we do not alert twice for the same job."""
    try:
        with SEEN_JOBS_FILE.open("w", encoding="utf-8") as file:
            json.dump(sorted(seen_jobs), file, indent=2)
    except OSError as error:
        print(f"Could not save {SEEN_JOBS_FILE.name}: {error}")


def normalize_text(text: str) -> str:
    """Turn repeated whitespace into single spaces and strip the ends."""
    return " ".join(text.split())


def build_job_id(title: str, location: str, link: str) -> str:
    """
    Build a repeatable ID for each job.

    If Amazon includes a job ID in the link, use that.
    Otherwise, fall back to a combination of title, location, and URL.
    """
    match = re.search(r"(JOB-[A-Z]{2}-\d+)", link, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()

    fallback = f"{title.lower()}|{location.lower()}|{link.lower()}"
    return fallback


def format_target_locations() -> str:
    """Return a nice beginner-friendly label for the target locations."""
    return ", ".join(f"{city}, {state}" for city, state in TARGET_LOCATIONS)


def find_matching_location(text: str) -> Optional[str]:
    """Return the target location label if the text matches one of our cities."""
    lowered = text.lower()
    has_state = bool(re.search(r"\bny\b", lowered)) or "new york" in lowered
    if not has_state:
        return None

    for city, state in TARGET_LOCATIONS:
        if city.lower() in lowered:
            return f"{city}, {state}"

    return None


def looks_like_target_job(text: str) -> bool:
    """Return True when the text looks like one of our target warehouse jobs."""
    has_location = find_matching_location(text) is not None
    has_warehouse_word = any(keyword in text.lower() for keyword in WAREHOUSE_KEYWORDS)
    return has_location and has_warehouse_word


def fetch_page(session: requests.Session) -> str:
    """
    Download the Amazon warehouse jobs HTML page and return the HTML.

    We scrape SEARCH_URL because the browser page at JOB_SEARCH_PAGE_URL is a
    JavaScript app that requests + BeautifulSoup cannot fully render.
    """
    response = session.get(
        SEARCH_URL,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text


def walk_json_items(data: object) -> Iterable[dict]:
    """Yield every dictionary found inside JSON data."""
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from walk_json_items(value)
    elif isinstance(data, list):
        for item in data:
            yield from walk_json_items(item)


def extract_jobs_from_json_ld(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Try to read JobPosting data from JSON-LD script tags.

    Some websites include job details in structured JSON for search engines.
    """
    jobs: List[Dict[str, str]] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue

        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue

        for item in walk_json_items(data):
            if item.get("@type") != "JobPosting":
                continue

            title = normalize_text(item.get("title", "Amazon Warehouse Job"))
            link = item.get("url", SEARCH_URL)

            location_text = ""
            job_location = item.get("jobLocation", {})
            if isinstance(job_location, list) and job_location:
                job_location = job_location[0]

            if isinstance(job_location, dict):
                address = job_location.get("address", {})
                parts = [
                    address.get("addressLocality", ""),
                    address.get("addressRegion", ""),
                ]
                location_text = normalize_text(", ".join(part for part in parts if part))

            description = item.get("description", "")
            description_text = BeautifulSoup(description, "html.parser").get_text(
                " ",
                strip=True,
            )
            combined_text = normalize_text(f"{title} {location_text} {description_text}")

            if not looks_like_target_job(combined_text):
                continue

            matched_location = find_matching_location(combined_text) or location_text

            jobs.append(
                {
                    "id": build_job_id(title, matched_location, link),
                    "title": title,
                    "location": matched_location,
                    "link": link,
                }
            )

    return jobs


def extract_jobs_from_links(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Fallback parser for pages that show jobs as normal HTML cards and links.

    We inspect links and the text around them, then look for our target cities.
    """
    jobs: List[Dict[str, str]] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue

        title = normalize_text(anchor.get_text(" ", strip=True))
        lower_href = href.lower()

        # Skip generic links unless the URL itself looks like a real job detail page.
        if title.lower() in GENERIC_LINK_TEXT and not (
            "jobid=" in lower_href
            or "applicationid=" in lower_href
            or "requisitionid=" in lower_href
        ):
            continue

        container = anchor
        container_text = title

        # Walk up a few levels to capture nearby location text from a card.
        for _ in range(3):
            if not getattr(container, "parent", None):
                break
            container = container.parent
            possible_text = normalize_text(container.get_text(" ", strip=True))
            if len(possible_text) > 800:
                break
            if possible_text:
                container_text = possible_text

        combined_text = normalize_text(f"{title} {container_text}")
        if not looks_like_target_job(combined_text):
            continue

        title_from_text = title or "Amazon Warehouse Job"
        link = urljoin(SEARCH_URL, href)

        matched_location = find_matching_location(combined_text) or format_target_locations()

        jobs.append(
            {
                "id": build_job_id(title_from_text, matched_location, link),
                "title": title_from_text,
                "location": matched_location,
                "link": link,
            }
        )

    return jobs


def deduplicate_jobs(jobs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Remove repeated job entries that point to the same job ID."""
    unique_jobs: List[Dict[str, str]] = []
    seen_ids: Set[str] = set()

    for job in jobs:
        if job["id"] in seen_ids:
            continue
        seen_ids.add(job["id"])
        unique_jobs.append(job)

    return unique_jobs


def find_matching_jobs(session: requests.Session) -> List[Dict[str, str]]:
    """Download the page and return matching warehouse jobs in our target cities."""
    html = fetch_page(session)
    soup = BeautifulSoup(html, "html.parser")

    jobs = extract_jobs_from_json_ld(soup)
    if not jobs:
        jobs = extract_jobs_from_links(soup)

    return deduplicate_jobs(jobs)


def create_session() -> requests.Session:
    """Create a requests session we can reuse for repeated Amazon checks."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def load_twilio_settings() -> Optional[Dict[str, str]]:
    """
    Read Twilio settings from environment variables.

    Return None if anything important is missing.
    """
    to_phone = os.getenv(ALERT_TO_PHONE_ENV, "").strip()
    settings = {
        "account_sid": os.getenv(TWILIO_ACCOUNT_SID_ENV, "").strip(),
        "auth_token": os.getenv(TWILIO_AUTH_TOKEN_ENV, "").strip(),
        "from_phone": os.getenv(TWILIO_FROM_PHONE_ENV, "").strip(),
        "to_phone": to_phone,
        # Twilio's official Sandbox for WhatsApp uses this shared sender.
        "whatsapp_from": os.getenv(
            TWILIO_WHATSAPP_FROM_ENV,
            "whatsapp:+14155238886",
        ).strip(),
        # By default we reuse the same destination number for WhatsApp.
        "to_whatsapp": os.getenv(
            ALERT_TO_WHATSAPP_ENV,
            f"whatsapp:{to_phone}" if to_phone else "",
        ).strip(),
    }

    required_keys = {
        "account_sid": TWILIO_ACCOUNT_SID_ENV,
        "auth_token": TWILIO_AUTH_TOKEN_ENV,
    }
    if SEND_CALL_ALERTS:
        required_keys["from_phone"] = TWILIO_FROM_PHONE_ENV
        required_keys["to_phone"] = ALERT_TO_PHONE_ENV
    if SEND_WHATSAPP_ALERTS:
        required_keys["whatsapp_from"] = TWILIO_WHATSAPP_FROM_ENV
        required_keys["to_whatsapp"] = ALERT_TO_WHATSAPP_ENV

    missing = [env_name for key, env_name in required_keys.items() if not settings[key]]
    if missing:
        print("Twilio is not fully configured yet for every alert type.")
        print("Set these environment variables before running the script:")
        for env_name in missing:
            print(f"- {env_name}")
        return None

    if SEND_WHATSAPP_ALERTS and settings["whatsapp_from"] == "whatsapp:+14155238886":
        print("Using the Twilio Sandbox for WhatsApp.")
        print("Make sure your phone has joined the sandbox in the Twilio Console.")

    return settings


def create_twilio_client(settings: Optional[Dict[str, str]]) -> Optional[Client]:
    """Create and return a Twilio client when settings are available."""
    if not settings:
        return None

    try:
        return Client(settings["account_sid"], settings["auth_token"])
    except Exception as error:
        print(f"Could not create Twilio client: {error}")
        return None


def format_syracuse_timestamp(moment: Optional[datetime] = None) -> str:
    """Return a timestamp in Syracuse, New York time."""
    if moment is None:
        moment = datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    local_time = moment.astimezone(SYRACUSE_TIMEZONE)
    return local_time.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def send_whatsapp_alert(
    client: Client,
    from_whatsapp: str,
    to_whatsapp: str,
    message: str,
) -> None:
    """Send a WhatsApp alert with Twilio."""
    client.messages.create(
        body=message,
        from_=from_whatsapp,
        to=to_whatsapp,
    )


def build_call_twiml(message: str) -> str:
    """Create the TwiML used for the automated phone call."""
    safe_message = escape(message)
    return f"<Response><Say>{safe_message}</Say></Response>"


def send_call_alert(client: Client, from_phone: str, to_phone: str, message: str) -> None:
    """Place an automated phone call with Twilio."""
    client.calls.create(
        twiml=build_call_twiml(message),
        from_=from_phone,
        to=to_phone,
    )


def send_twilio_alerts(
    client: Optional[Client],
    settings: Optional[Dict[str, str]],
    message: str,
) -> None:
    """Send WhatsApp and call alerts when Twilio is configured."""
    if not client or not settings:
        print("Twilio alerts were skipped because Twilio is not configured.")
        return

    if SEND_WHATSAPP_ALERTS:
        try:
            send_whatsapp_alert(
                client=client,
                from_whatsapp=settings["whatsapp_from"],
                to_whatsapp=settings["to_whatsapp"],
                message=message,
            )
            print("WhatsApp alert sent")
        except Exception as error:
            print(f"WhatsApp alert failed: {error}")

    if SEND_CALL_ALERTS:
        try:
            send_call_alert(
                client=client,
                from_phone=settings["from_phone"],
                to_phone=settings["to_phone"],
                message=message,
            )
            print("Phone call alert sent")
        except Exception as error:
            print(f"Phone call alert failed: {error}")


def create_starting_baseline(
    session: requests.Session,
    seen_jobs: Set[str],
) -> tuple[Set[str], bool]:
    """
    On the first successful run, save current jobs without alerting.

    This way, we only alert on jobs that appear after the monitor starts.
    """
    if seen_jobs:
        return seen_jobs, False

    current_jobs = find_matching_jobs(session)
    for job in current_jobs:
        seen_jobs.add(job["id"])

    save_seen_jobs(seen_jobs)

    if current_jobs:
        print(f"Saved {len(current_jobs)} existing job(s) as the starting baseline.")

    return seen_jobs, True


def build_job_alert_message(job: Dict[str, str]) -> str:
    """Create the message sent through WhatsApp and the phone call."""
    return (
        f"New Amazon warehouse job found: {job['title']} in "
        f"{job['location']}. Open Amazon job search here: "
        f"{JOB_SEARCH_PAGE_URL}"
    )


def print_new_job(job: Dict[str, str]) -> None:
    """Print the job details in a beginner-friendly format."""
    print(f"New job found: {job['title']} in {job['location']}")
    print(f"Open Amazon job search here: {JOB_SEARCH_PAGE_URL}")


def check_for_new_jobs(
    session: requests.Session,
    seen_jobs: Set[str],
    twilio_client: Optional[Client],
    twilio_settings: Optional[Dict[str, str]],
) -> Set[str]:
    """Run one Amazon check and send alerts only for brand-new jobs."""
    jobs = find_matching_jobs(session)
    new_jobs = [job for job in jobs if job["id"] not in seen_jobs]

    if new_jobs:
        for job in new_jobs:
            print_new_job(job)
            send_twilio_alerts(
                client=twilio_client,
                settings=twilio_settings,
                message=build_job_alert_message(job),
            )
            seen_jobs.add(job["id"])

        save_seen_jobs(seen_jobs)
    else:
        print("No new jobs found")

    return seen_jobs


def send_test_alert() -> None:
    """Send a labeled test alert without checking Amazon jobs."""
    twilio_settings = load_twilio_settings()
    twilio_client = create_twilio_client(twilio_settings)
    timestamp = format_syracuse_timestamp()
    message = (
        "TEST ALERT: GitHub Actions can reach your Amazon job monitor. "
        f"Sent at {timestamp} (Syracuse, NY time). "
        f"Open Amazon job search here: {JOB_SEARCH_PAGE_URL}"
    )
    send_twilio_alerts(
        client=twilio_client,
        settings=twilio_settings,
        message=message,
    )


def run_monitor_once() -> None:
    """
    Run a single check.

    This mode is useful for GitHub Actions, where each run starts fresh and
    then exits.
    """
    session = create_session()
    seen_jobs = load_seen_jobs()
    twilio_settings = load_twilio_settings()
    twilio_client = create_twilio_client(twilio_settings)

    seen_jobs, baseline_created = create_starting_baseline(session, seen_jobs)
    if baseline_created:
        print("Starting baseline is ready for future GitHub Actions runs.")
        return

    check_for_new_jobs(
        session=session,
        seen_jobs=seen_jobs,
        twilio_client=twilio_client,
        twilio_settings=twilio_settings,
    )


def parse_args() -> argparse.Namespace:
    """Read simple command-line options for local or GitHub Actions runs."""
    parser = argparse.ArgumentParser(
        description="Monitor Amazon warehouse jobs in Liverpool, NY and East Syracuse, NY.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one check and then exit.",
    )
    parser.add_argument(
        "--test-alert",
        action="store_true",
        help="Send a test WhatsApp message and phone call without scraping Amazon.",
    )
    return parser.parse_args()


def monitor_jobs() -> None:
    """Main loop: keep checking the page and alert only for brand-new jobs."""
    session = create_session()
    seen_jobs = load_seen_jobs()
    twilio_settings = load_twilio_settings()
    twilio_client = create_twilio_client(twilio_settings)

    try:
        seen_jobs, _ = create_starting_baseline(session, seen_jobs)
    except requests.RequestException as error:
        print(f"Could not create the starting baseline: {error}")
    except Exception as error:
        print(f"Unexpected setup error: {error}")

    print(f"Watching Amazon warehouse jobs in {format_target_locations()}...")
    print(f"Main Amazon search page: {JOB_SEARCH_PAGE_URL}")
    print("Press Ctrl+C to stop.")

    while True:
        try:
            seen_jobs = check_for_new_jobs(
                session=session,
                seen_jobs=seen_jobs,
                twilio_client=twilio_client,
                twilio_settings=twilio_settings,
            )

        except requests.RequestException as error:
            print(f"Network error while checking jobs: {error}")
        except Exception as error:
            print(f"Unexpected error: {error}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    arguments = parse_args()

    try:
        if arguments.test_alert:
            send_test_alert()
        elif arguments.once:
            run_monitor_once()
        else:
            monitor_jobs()
    except KeyboardInterrupt:
        print("\nStopped by user.")
