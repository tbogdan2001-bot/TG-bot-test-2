# postback.py
# Sends HTTP GET PostBack to Keitaro tracker to register a conversion.

import aiohttp
import logging

logger = logging.getLogger(__name__)


async def send_keitaro_postback(subid: str, postback_url_template: str):
    """
    Отправляет GET-запрос на Кейтаро для фиксации конверсии.
    subid — уникальный ID клика из ?start= параметра (e.g. AFF.122.42sasafaf43).
    postback_url_template — шаблон URL из .env, где {subid} заменяется реальным значением.
    """
    if not subid or not postback_url_template:
        logger.warning("PostBack не отправлен: пустой subid или URL шаблон")
        return

    url = postback_url_template.replace("{subid}", subid)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    logger.info(f"PostBack отправлен успешно для subid={subid}")
                else:
                    logger.warning(f"PostBack вернул статус {resp.status} для subid={subid}")
    except Exception as e:
        logger.error(f"Ошибка отправки PostBack для subid={subid}: {e}")
