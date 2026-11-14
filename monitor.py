import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

PAGES = [
    "https://www.sllc.ac.lk/exam-results",
    "https://www.sllc.ac.lk/exam-results/6",
]

STATE_FILE = "state.json"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 SLLCResultsMonitor/1.0"
}


def telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True
        },
        timeout=30
    )
    response.raise_for_status()


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_results():
    results = {}

    for page in PAGES:
        response = requests.get(
            page, headers=HEADERS, timeout=40
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            label = link.get_text(" ", strip=True)

            if "result" not in label.lower():
                continue

            parent = link.parent
            title = parent.get_text(" ", strip=True)

            if len(title) < 5:
                title = link.find_parent(["div", "tr", "li"])
                title = title.get_text(" ", strip=True) if title else label

            document_url = urljoin(page, link["href"])

            key = hashlib.sha256(
                f"{title}|{document_url}".encode()
            ).hexdigest()

            results[key] = {
                "title": title,
                "url": document_url,
                "page": page
            }

    if not results:
        raise RuntimeError(
            "No result links detected. Check website structure."
        )

    return results


def main():
    current = get_results()
    previous = load_state()

    # First run: establish baseline without sending old results.
    if previous is None:
        save_state(current)
        telegram(
            "SLLC Results Monitor is now active.\n"
            f"Recorded {len(current)} existing result entries."
        )
        return

    new_keys = set(current) - set(previous)

    for key in new_keys:
        item = current[key]
        telegram(
            "NEW SRI LANKA LAW COLLEGE RESULT\n\n"
            f"{item['title']}\n\n"
            f"Direct link: {item['url']}"
        )

    save_state(current)

    print(f"Checked {len(current)} entries.")
    print(f"New entries: {len(new_keys)}")


if __name__ == "__main__":
    main()
