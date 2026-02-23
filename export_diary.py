
import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.db.models import JournalEntry, User

async def export_html():
    user_uuid = "155175ec-b25c-4540-8deb-79e382d547cd"
    
    async with async_session() as db:
        user = await db.scalar(select(User).where(User.id == user_uuid))
        if not user: return

        result = await db.execute(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.entry_date.desc())
        )
        entries = result.scalars().all()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Diary Export</title>
            <style>
                body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
                .entry { margin-bottom: 40px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }
                .date { font-weight: bold; color: #555; }
                h1, h2, h3 { color: #333; }
                ul { padding-left: 20px; }
            </style>
        </head>
        <body>
            <h1>История дневника</h1>
        """
        
        for e in entries:
            text = e.final_diary_text or ""
            # Simple markdown to HTML conversion for display
            text = text.replace("**", "<b>").replace("**", "</b>")
            text = text.replace("- ", "<li>").replace("\n", "<br>")
            
            html += f"""
            <div class="entry">
                <div class="date">{e.entry_date}</div>
                <div class="content">{text}</div>
            </div>
            """
            
        html += "</body></html>"
        
        with open("diary_export.html", "w") as f:
            f.write(html)
        print("Exported to diary_export.html")

if __name__ == "__main__":
    asyncio.run(export_html())
