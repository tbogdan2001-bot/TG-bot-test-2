# ai_content.py
# NEW: AI Content Generation Module using Google Gemini API (google-generativeai SDK)
# Provides async post generation and personalized DM warmups in the assigned persona's voice,
# featuring a robust 3-retry attempt loop with automatic fallback to static configs on failures.

import asyncio
import logging
import google.generativeai as genai
import config

logger = logging.getLogger(__name__)

# Configure Gemini API if key is present
if config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set in config.py. Fallback templates will be used exclusively.")

# Content Plan fallback templates
STATIC_FALLBACKS = {
    "market_review": (
        "📊 **{persona_name} // ОБЗОР РЫНКА ({niche})**\n\n"
        "Привет! Давайте разберем текущую ситуацию на рынке. Крупные игроки сейчас активно аккумулируют "
        "позиции, пока толпа поддается панике. Это идеальный момент для входа в перспективные проекты! "
        "Не упустите возможность заработать на этой волне."
    ),
    "news": (
        "🔥 **ГОРЯЧИЕ НОВОСТИ // {persona_name}**\n\n"
        "Свежие события в нише: {niche}!\n"
        "Рынок гудит из-за последних регуляторных и технологических изменений. "
        "Те, кто успеет адаптироваться прямо сейчас, снимут сливки. Будьте в курсе обновлений в нашем канале!"
    ),
    "success_case": (
        "📈 **КЕЙС УСПЕХА // {persona_name}**\n\n"
        "Хочу поделиться результатом одного из моих учеников. "
        "Начав с полного нуля в {niche}, он применил пошаговый алгоритм и за месяц сделал +150% к банку! "
        "Система и дисциплина всегда бьют хаос и эмоции."
    ),
    "expert_tip": (
        "💡 **СОВЕТ ЭКСПЕРТА // {persona_name}**\n\n"
        "Мой главный совет по {niche} на сегодня:\n\n"
        "Никогда не заходите в сделку без четкого риск-менеджмента. Ограничивайте максимальный убыток "
        "до 1-2% от общего капитала. Это сохранит ваши нервы и депозит на дистанции!"
    ),
    "community_poll": (
        "❓ **ИНТЕРАКТИВ // Ваш опыт в {niche}**\n\n"
        "Друзья, мне крайне интересно узнать ваш текущий опыт!\n\n"
        "Какой ваш главный барьер, мешающий начать зарабатывать на этом прямо сейчас? "
        "Голосуйте в опросе на канале или пишите мне в личные сообщения!"
    ),
    "story": (
        "📖 **МОЯ ИСТОРИЯ // {persona_name}**\n\n"
        "Я тоже начинал с нуля, совершал глупые ошибки и терял депозиты. "
        "Но именно эти падения помогли мне выстроить надежную торговую/инвестиционную стратегию в {niche}. "
        "Помните: опыт приобретается только через практику!"
    ),
    "premium_teaser": (
        "💎 **ЗАКРЫТЫЙ ИНСАЙД // {persona_name}**\n\n"
        "Только что закончил анализ приватной сделки. "
        "Подобную аналитику мы выкладываем исключительно для участников закрытого клуба по {niche}. "
        "Внимательно следите за обновлениями в канале — скоро будет анонс!"
    ),
    "celebration": (
        "🎉 **ПРАЗДНИК & БЛАГОДАРНОСТЬ // {persona_name}**\n\n"
        "Сегодня особенный день! Наше сообщество растет с каждым часом, и я невероятно благодарен "
        "каждому из вас за доверие и активность. Вместе мы построим самое сильное комьюнити в сфере {niche}!"
    )
}

SYSTEM_PROMPTS = {
    "market_review": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write a high-converting, expert Telegram post reviewing the current market state in your niche.\n"
        "Be engaging, professional, and slightly dramatic. Use relevant emojis, bold text for headings.\n"
        "Write the output in Russian. The post must look like a ready-to-publish Telegram channel message. "
        "Max length is 1000 characters."
    ),
    "news": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write a short, breaking Telegram news post about recent important updates in your niche.\n"
        "Make it sound urgent and highly beneficial for the audience to read and take action.\n"
        "Write the output in Russian. Use relevant emojis, bold text for headings.\n"
        "Max length is 1000 characters."
    ),
    "success_case": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write an inspiring Telegram post detailing a subscriber success story.\n"
        "Explain how the student started with zero experience, applied your system, and achieved amazing results.\n"
        "Write the output in Russian. Use relevant emojis, bold text for headings.\n"
        "Max length is 1000 characters."
    ),
    "expert_tip": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write a short, highly actionable expert tip for Telegram.\n"
        "Focus on risk management, trading psychology, or a specific tactical step in your niche.\n"
        "Write the output in Russian. Use relevant emojis, bold text for headings.\n"
        "Max length is 1000 characters."
    ),
    "community_poll": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write an engaging Telegram post encouraging subscribers to participate in a poll or discussion.\n"
        "Ask a thought-provoking question about their main struggles or goals in this niche.\n"
        "Write the output in Russian. Use relevant emojis, bold text for headings.\n"
        "Max length is 1000 characters."
    ),
    "story": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write a personal story post about your own humble beginnings, mistakes made, and how you eventually succeeded.\n"
        "Build trust and show vulnerability. Make the reader realize they can do it too.\n"
        "Write the output in Russian. Use bold headings and clean formatting.\n"
        "Max length is 1000 characters."
    ),
    "premium_teaser": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write an exclusive premium teaser post for Telegram.\n"
        "Tease a highly profitable deal or strategy that is only available in your private group or mentorship program.\n"
        "Create high FOMO. Write the output in Russian. Use emojis.\n"
        "Max length is 1000 characters."
    ),
    "celebration": (
        "You are {persona_name}, {persona_description}. Your niche is {niche}.\n"
        "Write a warm celebration post thanking the subscribers for reaching a milestone or just expressing gratitude.\n"
        "Inspire unity, and reinforce that they are part of an elite, growing group.\n"
        "Write the output in Russian. Use warm, welcoming language and emojis.\n"
        "Max length is 1000 characters."
    )
}

async def generate_post(persona: dict, content_type: str, niche: str) -> str:
    """
    Generates a ready-to-publish Telegram channel post in the voice of the assigned persona using Google Gemini.
    Features robust retry logic (3 attempts) with a graceful fallback to a dynamic static template on failure.
    """
    if content_type not in SYSTEM_PROMPTS:
        logger.error(f"Unknown content type: {content_type}. Defaulting to market_review.")
        content_type = "market_review"

    # Setup the prompt
    sys_prompt = SYSTEM_PROMPTS[content_type].format(
        persona_name=persona["name"],
        persona_description=persona.get("description", ""),
        niche=niche
    )
    
    prompt = (
        "Напиши готовый для публикации пост в Telegram. Используй язык разметки Markdown "
        "(выделяй заголовки жирным шрифтом через **, списки делай аккуратными). "
        "Не пиши никакого лишнего текста до и после поста, только сам текст поста! "
        "Текст должен быть строго на русском языке и содержать смайлики. Длина поста не должна превышать 1024 символа."
    )

    # Retry loop
    for attempt in range(1, 4):
        try:
            if not config.GEMINI_API_KEY:
                raise ValueError("API Key is missing")
                
            logger.info(f"Gemini API request for post type '{content_type}' (Attempt {attempt}/3)...")
            
            # Using the fast, instruction-following gemini-1.5-flash model
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=sys_prompt
            )
            
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=800,
                    temperature=0.7,
                )
            )
            
            generated_text = response.text.strip()
            if generated_text:
                # Ensure length constraint
                if len(generated_text) > 1024:
                    generated_text = generated_text[:1020] + "..."
                logger.info("Successfully generated post using Gemini API.")
                return generated_text
                
        except Exception as e:
            logger.error(f"Gemini API attempt {attempt} failed: {e}")
            if attempt < 3:
                await asyncio.sleep(2 ** attempt) # Exponential backoff sleep

    # Fallback to static config-defined texts or hardcoded templates
    logger.warning(f"All Gemini attempts failed for post '{content_type}'. Falling back to static template.")
    fallback_tpl = STATIC_FALLBACKS.get(content_type, STATIC_FALLBACKS["market_review"])
    return fallback_tpl.format(
        persona_name=persona["name"],
        persona_description=persona.get("description", ""),
        niche=niche
    )

async def generate_warmup_message(persona: dict, stage: int, user_data: dict) -> str:
    """
    Generates a personalized direct warm-up message to a subscriber.
    Features robust retry logic (3 attempts) with a fallback to dynamic templates.
    """
    user_name = user_data.get("username", "")
    user_name_str = f" @{user_name}" if user_name and user_name != "unknown" else ""
    niche = persona["niche"]
    
    sys_prompt = (
        f"You are {persona['name']}, {persona.get('description', '')}. Your niche is {niche}.\n"
        f"Write a short, engaging direct message (DM) to warm up a user{user_name_str} at stage {stage} of the sales funnel.\n"
        f"Keep the message warm, extremely personalized, encouraging, and helpful. Use bold tags for accentuation.\n"
        f"Write in Russian in your unique expert voice. Use relevant emojis. Max 1000 characters."
    )
    
    prompt = (
        f"Напиши личное сообщение пользователю для прогрева. Это шаг {stage} прогрева. "
        "Текст должен быть лаконичным, мотивирующим и подталкивающим к изучению присланных материалов. "
        "Используй разметку Markdown (например, **текст**). Выдавай только текст сообщения без каких-либо приписок."
    )

    for attempt in range(1, 4):
        try:
            if not config.GEMINI_API_KEY:
                raise ValueError("API Key is missing")
                
            logger.info(f"Gemini API request for DM warmup stage {stage} (Attempt {attempt}/3)...")
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=sys_prompt
            )
            
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=600,
                    temperature=0.8,
                )
            )
            
            generated_text = response.text.strip()
            if generated_text:
                if len(generated_text) > 1024:
                    generated_text = generated_text[:1020] + "..."
                logger.info(f"Successfully generated DM warmup for stage {stage} using Gemini API.")
                return generated_text
                
        except Exception as e:
            logger.error(f"Gemini DM warmup attempt {attempt} failed: {e}")
            if attempt < 3:
                await asyncio.sleep(2 ** attempt)

    # Robust fallback based on config/stage
    logger.warning(f"All Gemini attempts failed for DM warmup stage {stage}. Falling back to default.")
    
    # Let's pull from config.CONTENT_PLAN if stage matches a warmup index
    warmup_index = stage - 1
    if 0 <= warmup_index < len(config.CONTENT_PLAN):
        seq = config.CONTENT_PLAN[warmup_index]
        return seq["text"].format(
            persona_name=persona["name"],
            persona_description=persona.get("description", ""),
            niche=niche,
            channel_name=config.CHANNEL_NAME
        )
        
    return (
        f"👋 Привет{user_name_str}! Это {persona['name']}.\n\n"
        f"Надеюсь, ты активно изучаешь наши материалы по {niche}. "
        f"Если у тебя возникли какие-либо вопросы — не стесняйся, пиши мне напрямую. Рад помочь!"
    )
