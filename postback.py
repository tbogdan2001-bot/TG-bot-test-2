# postback.py
# Sends a GET PostBack request to Keitaro to register a conversion when a user subscribes.

import aiohttp
import logging

logger = logging.getLogger(__name__)

async def send_keitaro_postback(subid: str, postback_url_template: str):
    """
    Sends a GET request to Keitaro to register a conversion.
    subid — unique click ID from the ?start= parameter.
    postback_url_template — URL template with {subid} placeholder from config.
    """
    if not subid or not postback_url_template:
        logger.warning("PostBack not sent: empty subid or URL template.")
        return

    url = postback_url_template.replace("{subid}", subid)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    logger.info(f"PostBack sent successfully for subid={subid}")
                else:
                    logger.warning(f"PostBack returned status {resp.status} for subid={subid}")
    except Exception as e:
        logger.error(f"Error sending PostBack for subid={subid}: {e}")
