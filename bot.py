import os
import asyncio
from datetime import datetime
from collections import Counter

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import aiosqlite
import networkx as nx
from dotenv import load_dotenv

# ------------------------- Загрузка переменных окружения -------------------------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()  # В aiogram 3.x Dispatcher создается без аргументов

DB = "ops.db"

# ------------------------- Инициализация базы -------------------------
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS cases(
            id INTEGER PRIMARY KEY,
            title TEXT,
            created TEXT
        );

        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY,
            case_id INTEGER,
            text TEXT,
            ts TEXT
        );

        CREATE TABLE IF NOT EXISTS persons(
            id INTEGER PRIMARY KEY,
            name TEXT
        );

        CREATE TABLE IF NOT EXISTS links(
            a TEXT,
            b TEXT,
            type TEXT
        );
        """)
        await db.commit()

# ------------------------- Модули -------------------------

# RegistryAdapter (разрешенные реестры)
class RegistryAdapter:
    async def search_company(self, name: str):
        return {
            "source": "open_registry",
            "result": f"Найдена организация: {name}",
            "status": "ok"
        }
registry = RegistryAdapter()

# AgencyAdapter (ведомственные API)
class AgencyAdapter:
    async def query(self, endpoint, payload):
        return {
            "endpoint": endpoint,
            "status": "connected",
            "data": payload
        }
agency = AgencyAdapter()

# TextAnalyzer
class TextAnalyzer:
    def analyze_protocol(self, text):
        words = text.lower().split()
        freq = Counter(words).most_common(5)
        return {
            "words": len(words),
            "top_terms": freq,
            "has_dates": any(x.isdigit() and len(x)==4 for x in words)
        }
analyzer = TextAnalyzer()

# DocMatcher
class DocMatcher:
    def similarity(self, a, b):
        sa = set(a.lower().split())
        sb = set(b.lower().split())
        return len(sa & sb) / max(len(sa | sb), 1)
matcher = DocMatcher()

# RiskEngine
class RiskEngine:
    def score(self, factors: dict):
        score = 0
        if factors.get("violence"): score += 5
        if factors.get("repeat"): score += 3
        if factors.get("weapons"): score += 4
        if factors.get("group"): score += 2

        level = "LOW"
        if score >= 5: level = "MEDIUM"
        if score >= 9: level = "HIGH"
        return score, level
risk_engine = RiskEngine()

# ------------------------- Граф связей -------------------------
graph = nx.Graph()

def add_link(a, b, t):
    graph.add_edge(a, b, type=t)

def graph_report(node):
    if node not in graph:
        return "Нет связей"
    neighbors = list(graph.neighbors(node))
    return f"Связи: {', '.join(neighbors)}"

# ------------------------- Вспомогательные функции -------------------------
async def case_summary(case_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT text, ts FROM events WHERE case_id=? ORDER BY ts",
            (case_id,))
        rows = await cur.fetchall()
    if not rows:
        return "Нет событий"
    timeline = "\n".join([f"{r[1][:16]} — {r[0]}" for r in rows])
    return timeline

# ------------------------- Команды -------------------------

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer("Служебный бот расширенной аналитики запущен ✅")

@dp.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer(
        "/start — запустить бота\n"
        "/help — помощь\n"
        "/case Заголовок — создать дело\n"
        "/event ID|Описание — добавить событие\n"
        "/timeline ID — таймлайн по делу\n"
        "/registry Название — поиск в открытых реестрах\n"
        "/agency — пример запроса к ведомственному API\n"
        "/analyze Текст — анализ протокола\n"
        "/match Текст1|Текст2 — сравнение документов\n"
        "/risk Текст — оценка риска\n"
        "/link A B тип — добавить связь\n"
        "/graph Узел — показать связи\n"
        "/template — процессуальный шаблон"
    )

# ---------- CASE ----------
@dp.message(Command("case"))
async def new_case(msg: Message):
    title = msg.text.replace("/case", "").strip()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO cases(title,created) VALUES(?,?)",
            (title, datetime.now().isoformat()))
        await db.commit()
    await msg.answer("Дело создано ✅")

# ---------- EVENT ----------
@dp.message(Command("event"))
async def add_event(msg: Message):
    data = msg.text.replace("/event", "").strip()
    if "|" not in data:
        await msg.answer("Формат: /event ID|Описание")
        return
    case_id, text = data.split("|", 1)
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO events(case_id,text,ts) VALUES(?,?,?)",
            (case_id, text, datetime.now().isoformat()))
        await db.commit()
    await msg.answer("Событие добавлено ✅")

@dp.message(Command("timeline"))
async def timeline(msg: Message):
    parts = msg.text.split()
    if len(parts)<2:
        await msg.answer("Формат: /timeline ID")
        return
    cid = parts[1]
    s = await case_summary(cid)
    await msg.answer(s)

# ---------- REGISTRY ----------
@dp.message(Command("registry"))
async def registry_search(msg: Message):
    q = msg.text.replace("/registry", "").strip()
    r = await registry.search_company(q)
    await msg.answer(str(r))

# ---------- AGENCY ----------
@dp.message(Command("agency"))
async def agency_call(msg: Message):
    r = await agency.query("check", {"q": "test"})
    await msg.answer(str(r))

# ---------- PROTOCOL ANALYSIS ----------
@dp.message(Command("analyze"))
async def analyze_text(msg: Message):
    text = msg.text.replace("/analyze", "").strip()
    r = analyzer.analyze_protocol(text)
    await msg.answer(str(r))

# ---------- DOC MATCH ----------
@dp.message(Command("match"))
async def match_docs(msg: Message):
    data = msg.text.replace("/match", "").strip()
    if "|" not in data:
        await msg.answer("Формат: /match Текст1|Текст2")
        return
    a, b = data.split("|",1)
    s = matcher.similarity(a, b)
    await msg.answer(f"Сходство: {round(s*100,1)}%")

# ---------- RISK ----------
@dp.message(Command("risk"))
async def risk(msg: Message):
    text = msg.text.replace("/risk", "").lower()
    factors = {
        "violence": "violence" in text,
        "repeat": "repeat" in text,
        "weapons": "weapons" in text,
        "group": "group" in text
    }
    score, level = risk_engine.score(factors)
    await msg.answer(f"Риск: {level} ({score})")

# ---------- GRAPH ----------
@dp.message(Command("link"))
async def link(msg: Message):
    parts = msg.text.split()
    if len(parts)<4:
        await msg.answer("Формат: /link A B тип")
        return
    _, a, b, t = parts
    add_link(a, b, t)
    await msg.answer("Связь добавлена ✅")

@dp.message(Command("graph"))
async def graph_cmd(msg: Message):
    parts = msg.text.split()
    if len(parts)<2:
        await msg.answer("Формат: /graph Узел")
        return
    node = parts[1]
    await msg.answer(graph_report(node))

# ---------- TEMPLATES ----------
@dp.message(Command("template"))
async def template(msg: Message):
    await msg.answer(
        "Процессуальный шаблон:\nДата:\nОснование:\nУстановлено:\nДоказательства:\nМеры:\nПодпись:"
    )

# ------------------------- RUN -------------------------
async def main():
    await init_db()
    await dp.start_polling(bot)

asyncio.run(main())
