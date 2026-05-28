# postback.py
# Sends a Keitaro PostBack HTTP request when a user confirms subscription.
# Called from main.py after successful subscription check.

import aiohttp
import logging

logger = logging.getLogger(__name__)

async def send_keitaro_postback(subid: str, postback_url: str) -> bool:
    """
    Fires a GET request to the Keitaro PostBack URL with the user's subid.
    Returns True if the request was successful (HTTP 200), False otherwise.

    Args:
        subid: The Keitaro click ID (subid) stored in the user's DB record.
        postback_url: Base PostBack URL from config.KEITARO_POSTBACK_URL.
                      Example: http://89.125.50.94/postback?token=YOUR_TOKEN
    """
    if not subid or not postback_url:
        logger.warning("PostBack skipped: subid or postback_url is empty.")
        return False

    # Append subid param if not already present as a template placeholder
    if "{subid}" in postback_url:
        url = postback_url.replace("{subid}", subid).replace("{status}", "approved")
    else:
        separator = "&" if "?" in postback_url else "?"
        url = f"{postback_url}{separator}subid={subid}&status=approved"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    logger.info(f"Keitaro PostBack SUCCESS: subid={subid}, url={url}, status={response.status}")
                    return True
                else:
                    logger.warning(f"Keitaro PostBack WARNING: subid={subid}, url={url}, status={response.status}")
                    return False
    except Exception as e:
        logger.error(f"Keitaro PostBack ERROR: subid={subid}, url={url}, error={e}")
        return False
