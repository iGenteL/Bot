import asyncio
import aiohttp
import os
import random
import logging
from typing import List
from aiohttp import ClientSession

# ========== Settings ==========
CHANNEL_ID = "1373728039158022144"
DELAY = 1.2  # Delay between message rounds
MODE = "ordered"  # "ordered" or "random"

# ========== File Paths ==========
TOKENS_FILE = "tokens.txt"
MESSAGES_FILE = "messages.txt"
MENTIONS_FILE = "mentions.txt"

# ========== Setup Logging ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ========== Load and Clean Files ==========
def load_clean_file(path: str) -> List[str]:
    try:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip().replace('"', '') for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        return []

tokens = load_clean_file(TOKENS_FILE)
messages = load_clean_file(MESSAGES_FILE)
mentions = load_clean_file(MENTIONS_FILE)

if not tokens or not messages:
    logger.error("tokens.txt or messages.txt is empty.")
    exit()

# ========== Mentions ==========
mentions_text = " ".join([f"<@{m}>" for m in mentions]) if mentions else ""

# ========== Send Message ==========
async def send_message(session: ClientSession, token: str, message: str) -> None:
    url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    payload = {"content": f"{mentions_text} {message}".strip()}

    try:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                logger.info(f"Token: {token[:10]}... | Message sent")
            elif response.status == 401:
                logger.warning(f"Token: {token[:10]}... | Invalid token (401) - Removed")
                if token in tokens:
                    tokens.remove(token)
            elif response.status == 429:
                retry_after = (await response.json()).get("retry_after", 5)
                logger.warning(f"Token: {token[:10]}... | Rate Limited (429) - Waiting {retry_after}s")
                await asyncio.sleep(float(retry_after))
            else:
                logger.error(f"Token: {token[:10]}... | Status: {response.status}")
    except Exception as e:
        logger.error(f"Token: {token[:10]}... | Exception: {e}")

# ========== Send Messages in Parallel ==========
async def send_message_batch(session: ClientSession, message: str, current_tokens: List[str]) -> None:
    tasks = []
    for token in current_tokens:
        tasks.append(send_message(session, token, message))
    await asyncio.gather(*tasks, return_exceptions=True)

# ========== Main Loop ==========
async def main():
    logger.info("Started sending messages...")
    async with aiohttp.ClientSession() as session:
        try:
            while True:
                for message in messages:
                    current_tokens = tokens.copy()
                    if MODE == "random":
                        random.shuffle(current_tokens)
                    await send_message_batch(session, message, current_tokens)
                    await asyncio.sleep(DELAY)
        except asyncio.CancelledError:
            logger.info("Stopped by user.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

# ========== Run ==========
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")