
import asyncio
from app.db.engine import async_session
from app.db.models import BotSettings
from sqlalchemy import select
from app.services.crypto import decrypt_value
from app.config import settings

async def diag():
    print(f"ENCRYPTION_KEY exists: {bool(settings.ENCRYPTION_KEY)}")
    async with async_session() as session:
        res = await session.execute(select(BotSettings))
        settings_list = res.scalars().all()
        print(f"Total settings in DB: {len(settings_list)}")
        for s in settings_list:
            val = s.value
            if s.is_secret:
                val = decrypt_value(s.encrypted_value)
                print(f"KEY: {s.key} | Secret: Yes | Decrypted: {'[Decrypted Successfully]' if val != '[Decryption Failed]' else '[FAILED]'}")
            else:
                print(f"KEY: {s.key} | value: {s.value}")

if __name__ == '__main__':
    asyncio.run(diag())
