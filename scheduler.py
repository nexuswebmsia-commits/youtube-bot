"""
Daily YouTube Video Scheduler
"""

import os
import sys
import time
import json
import random
import logging
import argparse
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

POST_TIME = os.getenv("SCHEDULER_POST_TIME", "09:00")
PROMPT_QUEUE_FILE = os.getenv("PROMPT_QUEUE_FILE", "prompt_queue.json")

MY_PROMPTS = [
    "a golden retriever puppy sliding on a hardwood floor and crashing into a wall",
    "a cat dramatically falling off a table after being startled by a cucumber",
    "a tiny hamster attempting to eat a giant piece of broccoli",
    "a corgi running in slow motion through a field of flowers",
    "a parrot dancing to salsa music on a kitchen counter",
    "a baby goat hopping around a barnyard knocking things over",
    "a raccoon getting caught stealing french fries from a fast food bag",
    "a penguin waddling and slipping on ice in an exaggerated way",
    "a dog failing repeatedly to catch a treat thrown into the air",
    "a cat squeezing itself into a box that is clearly too small",
]

DEFAULT_TITLE_PREFIX = os.getenv("DEFAULT_TITLE_PREFIX", "Funny Animal Video")
DEFAULT_DESCRIPTION = os.getenv("DEFAULT_DESCRIPTION", "Daily funny animal content generated with AI. Subscribe for more!")
DEFAULT_TAGS = ["funny animals", "cute animals", "AI generated", "funny pets", "animal videos"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("scheduler.log")])
log = logging.getLogger(__name__)

def load_queue():
    if Path(PROMPT_QUEUE_FILE).exists():
        with open(PROMPT_QUEUE_FILE) as f:
            return json.load(f)
    queue = MY_PROMPTS.copy()
    random.shuffle(queue)
    save_queue(queue)
    return queue

def save_queue(queue):
    with open(PROMPT_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)

def ai_generate_prompts(n=5):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return random.sample(MY_PROMPTS, min(n, len(MY_PROMPTS)))
    try:
        resp = requests.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json={"model": "claude-sonnet-4-20250514", "max_tokens": 512, "messages": [{"role": "user", "content": f"Generate {n} short funny animal video prompts. Return ONLY a JSON array of strings."}]}, timeout=30)
        resp.raise_for_status()
        raw = resp.json()["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        log.error(f"Failed to generate prompts: {e}")
        return random.sample(MY_PROMPTS, min(n, len(MY_PROMPTS)))

def next_prompt():
    queue = load_queue()
    if not queue:
        queue = ai_generate_prompts(n=10)
        random.shuffle(queue)
    prompt = queue.pop(0)
    save_queue(queue)
    return prompt

def post_video():
    from server import YouTubeMCP
    prompt = next_prompt()
    title = f"{DEFAULT_TITLE_PREFIX} — {datetime.now().strftime('%b %d, %Y')}"
    mcp = YouTubeMCP()
    result = mcp.create_funny_animal_video(prompts=[prompt], title=title, description=DEFAULT_DESCRIPTION, tags=DEFAULT_TAGS, privacy_status="public")
    log.info(f"Upload complete: https://youtu.be/{result['videoId']}")
    return result

def seconds_until(time_str):
    from datetime import timedelta
    now = datetime.now()
    h, m = map(int, time_str.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()

def run_scheduler():
    log.info(f"Scheduler started. Will post daily at {POST_TIME}.")
    while True:
        wait = seconds_until(POST_TIME)
        time.sleep(wait)
        try:
            post_video()
        except Exception as e:
            log.error(f"Post failed: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now", action="store_true")
    args = parser.parse_args()
    if args.run_now:
        post_video()
    else:
        run_scheduler()
