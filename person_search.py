import asyncio
from collections import Counter
from difflib import SequenceMatcher

# ------------------------- PERSON SEARCH MODULE -------------------------
class PersonSearchModule:

    def __init__(self):
        # Пример открытых записей (демо)
        self.public_records = [
            {"fio": "Иванов Иван Иванович", "birth": "01.01.1990",
             "source": "Судебное решение", "note": "Упоминание в публикации"},
            {"fio": "Петров Петр Сергеевич", "birth": "12.05.1985",
             "source": "Реестр ИП", "note": "Зарегистрирован как ИП"},
        ]
        # Возможные варианты сокращений и ошибок
        self.variants = {
            "Иван": ["Ивн", "Иванн"],
            "Петр": ["Петя", "Петэр"],
        }

    # 1️⃣ Авто-нормализация ФИО
    def normalize(self, s: str):
        return s.lower().replace("ё", "е").strip()

    # 2️⃣ Нечёткий поиск
    def fuzzy_match(self, a: str, b: str):
        a = self.normalize(a)
        b = self.normalize(b)
        return SequenceMatcher(None, a, b).ratio()

    # 3️⃣ Генерация вариантов ФИО
    def generate_variants(self, surname, name, patronymic):
        names = [name]
        if name in self.variants:
            names.extend(self.variants[name])
        return [(surname, n, patronymic) for n in names]

    # 4️⃣ Основной поиск
    async def search(self, surname, name, patronymic, birth=None):
        query_variants = self.generate_variants(surname, name, patronymic)
        results = []

        for rec in self.public_records:
            for v in query_variants:
                fio_variant = f"{v[0]} {v[1]} {v[2]}"
                score = self.fuzzy_match(rec["fio"], fio_variant)
                birth_match = True if not birth else rec["birth"] == birth
                if score > 0.7 and birth_match:
                    results.append({
                        "fio": rec["fio"],
                        "birth": rec["birth"],
                        "source": rec["source"],
                        "note": rec["note"],
                        "score": round(score, 2)
                    })
        return results

    # 5️⃣ Авто-сводка
    def summarize(self, results):
        if not results:
            return "Совпадений в открытых источниках не найдено."

        text = "Сводка по найденным упоминаниям:\n\n"
        for r in results:
            text += (
                f"ФИО: {r['fio']}\n"
                f"Дата рождения: {r['birth']}\n"
                f"Источник: {r['source']}\n"
                f"Примечание: {r['note']}\n"
                f"Достоверность: {r['score']*100:.0f}%\n\n"
            )
        return text

    # 6️⃣ Экспорт отчета в текст
    def export_report(self, results):
        return self.summarize(results)


# Инициализация модуля
person_search = PersonSearchModule()
