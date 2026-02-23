"""
Weekly summary generation service.
Collects entries for the last 7 days and uses LLM to create a summary.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import JournalEntry, User
from app.services.pipeline import get_llm_provider
from app.config import settings
from app.dto.llm import LLMRequestDTO
import uuid

logger = logging.getLogger(__name__)

WEEKLY_SUMMARY_PROMPT = """Ты — опытный психолог и коуч. Твоя задача — проанализировать дневниковые записи пользователя за последнюю неделю и составить вдохновляющий и глубокий итог.

ИТОГ ДОЛЖЕН ВКЛЮЧАТЬ:
1. **Общий тон недели**: Какое было преобладающее настроение (используй данные о настроении записей)?
2. **Ключевые события**: Что самого важного произошло?
3. **Достижения и прогресс**: В чем пользователь молодец? (даже если это маленькие шаги).
4. **Закономерности**: Какие повторяющиеся мысли или трудности ты заметил?
5. **Фокус на следующую неделю**: Дай один мягкий, но точный совет или вопрос для размышления.

ФОРМАТ (HTML):
- Используй <b>заголовки</b> и пункты "•". 
- Тон должен быть поддерживающим, эмпатичным и профессиональным.
- Язык: русский.
- Не используй ```блоки кода```.
"""

async def generate_weekly_summary(db: AsyncSession, user: User) -> str:
    """Gather entries and call LLM for summary."""
    
    # 1. Get entries for last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    q = select(JournalEntry).where(
        and_(
            JournalEntry.user_id == user.id,
            JournalEntry.created_at >= seven_days_ago,
            JournalEntry.status == "ok"
        )
    ).order_by(JournalEntry.created_at.asc())
    
    result = await db.execute(q)
    entries = result.scalars().all()
    
    if not entries:
        return "На этой неделе у тебя не было записей. Начни завтра, чтобы в следующее воскресенье я подготовил для тебя итог! ✨"

    # 2. Prepare text for LLM
    full_text = ""
    for e in entries:
        full_text += f"Дата: {e.created_at.strftime('%Y-%m-%d')} | Настроение: {e.mood or 'не определено'}\n{e.final_diary_text}\n---\n"

    # 3. Call LLM
    from app.services.settings import DynamicSettings
    ds = DynamicSettings(db)
    
    provider_name = await ds.get_llm_provider()
    model_name = await ds.get_llm_model(provider_name)
    api_key = await ds.get_llm_api_key(provider_name)
    
    llm_provider = get_llm_provider(provider_name, api_key=api_key, model=model_name)
    
    prompt = WEEKLY_SUMMARY_PROMPT
    if user.summary_instructions:
        prompt += f"\n\nДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ ОТ ПОЛЬЗОВАТЕЛЯ:\n{user.summary_instructions}"

    llm_req = LLMRequestDTO(
        request_id=str(uuid.uuid4()),
        provider=provider_name,
        model=model_name,
        system_prompt=prompt,
        user_prompt=f"Вот мои записи за неделю:\n\n{full_text}",
        temperature=0.7,
        max_tokens=2000
    )
    
    llm_result = await llm_provider.generate(llm_req)
    
    if llm_result.status != "ok":
        logger.error(f"Failed to generate summary for user {user.id}: {llm_result.error_message}")
        return "Извини, возникла ошибка при создании твоего итога недели. Мы уже чиним! 🛠"

    return llm_result.final_text
