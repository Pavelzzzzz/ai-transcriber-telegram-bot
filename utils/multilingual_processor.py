"""
Интеллектуальная обработка текста с поддержкой нескольких языков
"""

import logging
import re
from dataclasses import dataclass

# Базовые зависимости
try:
    from langdetect import detect

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logging.warning("langdetect not available - using basic detection")

try:
    from spellchecker import SpellChecker

    SPELLCHECKER_AVAILABLE = True
except ImportError:
    SPELLCHECKER_AVAILABLE = False
    logging.warning("spellchecker not available - using built-in corrections")

logger = logging.getLogger(__name__)


@dataclass
class TextCorrection:
    """Информация об исправлении"""

    original: str
    corrected: str
    type: str  # 'spelling', 'grammar', 'punctuation', 'capitalization'
    language: str
    description: str


@dataclass
class TextAnalysisResult:
    """Результат анализа текста"""

    original_text: str
    corrected_text: str
    language: str
    corrections: list[TextCorrection]
    stats: dict[str, int]
    recommendations: list[str]


class MultilingualTextProcessor:
    """Многоязычный процессор текста"""

    def __init__(self):
        self.language_patterns = self._init_language_patterns()
        self.glyph_patterns = self._init_glyph_patterns()

        # Инициализация спеллчекеров
        self.spell_checkers = {}
        if SPELLCHECKER_AVAILABLE:
            try:
                self.spell_checkers["en"] = SpellChecker(language="en")
                self.spell_checkers["ru"] = SpellChecker(language="ru")
            except Exception as e:
                logger.warning(f"Spell checker initialization failed: {e}")

    def _init_language_patterns(self) -> dict[str, dict]:
        """Инициализация языковых паттернов"""
        return {
            "ru": {
                "name": "Русский",
                "abbreviations": {
                    "т.к.": "так как",
                    "т.е.": "то есть",
                    "т.д.": "и так далее",
                    "т.п.": "и тому подобное",
                    "др.": "другие",
                    "пр.": "прочее",
                    "см.": "смотри",
                    "г.": "город",
                    "ул.": "улица",
                    "д.": "дом",
                    "кв.": "квартира",
                    "обл.": "область",
                    "р-н": "район",
                },
                "common_errors": {
                    "превет": "привет",
                    "спосибо": "спасибо",
                    "заранеее": "заранее",
                    "харошо": "хорошо",
                    "намнаго": "намного",
                    "сайз": "раз",
                    "придти": "прийти",
                    "зделать": "сделать",
                    "бальшой": "большой",
                    "пожалуста": "пожалуйста",
                    "извиняюсь": "извините",
                    "вранье": "враньё",
                    "читать": "читать",
                    "много": "много",
                },
                "punctuation_patterns": [
                    (r"(\s+)([,.!?;:])", r"\2"),  # Удалить пробелы перед знаками
                    (r"([,.!?;:])(?=\S)", r"\1 "),  # Добавить пробелы после знаков
                    (r"([.!?]){3,}", r"\1"),  # Множественные знаки
                    (r"\s+", " "),  # Двойные пробелы
                ],
                "capitalization_rules": {
                    "sentence_start": True,
                    "proper_nouns": True,
                    "abbreviations": ["г", "ул", "д", "кв", "обл", "р-н"],
                },
            },
            "en": {
                "name": "English",
                "abbreviations": {
                    "i.e.": "that is",
                    "e.g.": "for example",
                    "etc.": "et cetera",
                    "mr.": "mister",
                    "mrs.": "missus",
                    "dr.": "doctor",
                    "prof.": "professor",
                    "st.": "saint",
                    "ave.": "avenue",
                    "blvd.": "boulevard",
                    "apt.": "apartment",
                    "no.": "number",
                },
                "common_errors": {
                    "recieve": "receive",
                    "beleive": "believe",
                    "occured": "occurred",
                    "untill": "until",
                    "wich": "which",
                    "whith": "with",
                    "teh": "the",
                    "adn": "and",
                    "taht": "that",
                    "thier": "their",
                    "alot": "a lot",
                    "seperate": "separate",
                    "definately": "definitely",
                    "neccessary": "necessary",
                    "accomodate": "accommodate",
                    "begining": "beginning",
                    "goverment": "government",
                    "occurence": "occurrence",
                    "publically": "publicly",
                    "priviledge": "privilege",
                },
                "punctuation_patterns": [
                    (r"(\s+)([,.!?;:])", r"\2"),
                    (r"([,.!?;:])(?=\S)", r"\1 "),
                    (r"([.!?]){3,}", r"\1"),
                    (r"\s+", " "),
                ],
                "capitalization_rules": {
                    "sentence_start": True,
                    "proper_nouns": True,
                    "abbreviations": ["mr", "mrs", "dr", "prof", "st", "ave", "blvd", "apt", "no"],
                },
            },
        }

    def _init_glyph_patterns(self) -> dict[str, str]:
        """Инициализация паттернов для определения языка"""
        return {"ru": "[а-яё]", "en": "[a-z]", "mixed": "[а-яёa-z]"}

    def detect_language(self, text: str) -> str:
        """Определение языка текста"""
        if not text or not text.strip():
            return "unknown"

        try:
            # Проверяем наличие русских символов
            if re.search(r"[а-яё]", text, re.IGNORECASE):
                # Проверяем преобладание русских символов
                ru_chars = len(re.findall(r"[а-яё]", text, re.IGNORECASE))
                en_chars = len(re.findall(r"[a-z]", text, re.IGNORECASE))

                if ru_chars > en_chars:
                    return "ru"
                elif en_chars > ru_chars:
                    return "en"
                else:
                    return "mixed"

            # Проверяем английские символы
            if re.search(r"[a-z]", text, re.IGNORECASE):
                return "en"

            # Используем langdetect если доступен
            if LANGDETECT_AVAILABLE and len(text) > 10:
                detected = detect(text)
                if detected in ["ru", "en"]:
                    return detected

            return "unknown"

        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "unknown"

    def correct_spelling(self, text: str, language: str) -> tuple[str, list[TextCorrection]]:
        """Исправление орфографических ошибок"""
        corrections = []
        corrected = text

        if language not in self.language_patterns:
            return corrected, corrections

        patterns = self.language_patterns[language]

        # Использование спеллчекера если доступен
        if SPELLCHECKER_AVAILABLE and language in self.spell_checkers:
            try:
                words = text.split()
                corrected_words = []

                for word in words:
                    # Очищаем слово от пунктуации
                    clean_word = re.sub(r"[^\w]", "", word)

                    if clean_word and len(clean_word) > 2:
                        spell = self.spell_checkers[language]

                        # Проверяем орфографию
                        if clean_word.lower() not in spell:
                            candidates = spell.candidates(clean_word.lower())
                            if candidates:
                                # Выбираем наиболее вероятный вариант
                                suggestion = list(candidates)[0]
                                if suggestion != clean_word.lower():
                                    # Сохраняем регистр
                                    if clean_word[0].isupper():
                                        suggestion = suggestion.capitalize()

                                    corrected_words.append(word.replace(clean_word, suggestion))

                                    corrections.append(
                                        TextCorrection(
                                            original=clean_word,
                                            corrected=suggestion,
                                            type="spelling",
                                            language=language,
                                            description=f"Исправлена орфография: '{clean_word}' → '{suggestion}'",
                                        )
                                    )
                                else:
                                    corrected_words.append(word)
                            else:
                                corrected_words.append(word)
                        else:
                            corrected_words.append(word)
                    else:
                        corrected_words.append(word)

                corrected = " ".join(corrected_words)

            except Exception as e:
                logger.warning(f"Spell checking failed: {e}")

        # Исправление распространенных ошибок из словаря
        for wrong, right in patterns["common_errors"].items():
            if wrong in corrected.lower():
                # Заменяем с учетом регистра
                pattern = re.compile(r"\b" + re.escape(wrong) + r"\b", re.IGNORECASE)
                matches = pattern.findall(corrected)

                if matches:
                    corrected = pattern.sub(right, corrected)
                    corrections.append(
                        TextCorrection(
                            original=wrong,
                            corrected=right,
                            type="spelling",
                            language=language,
                            description=f"Исправлена частая ошибка: '{wrong}' → '{right}'",
                        )
                    )

        return corrected, corrections

    def correct_grammar(self, text: str, language: str) -> tuple[str, list[TextCorrection]]:
        """Исправление грамматических ошибок"""
        corrections = []
        corrected = text

        if language not in self.language_patterns:
            return corrected, corrections

        patterns = self.language_patterns[language]

        # Расширение сокращений
        for abbrev, expansion in patterns["abbreviations"].items():
            if abbrev in corrected:
                corrected = corrected.replace(abbrev, expansion)
                corrections.append(
                    TextCorrection(
                        original=abbrev,
                        corrected=expansion,
                        type="grammar",
                        language=language,
                        description=f"Расширено сокращение: '{abbrev}' → '{expansion}'",
                    )
                )

        # Базовые грамматические правила
        if language == "ru":
            # Исправление двойных отрицаний (простые случаи)
            corrected = re.sub(r"\bне\b\s+\bникогда\b", "никогда", corrected, flags=re.IGNORECASE)
            corrected = re.sub(r"\bне\b\s+\bни\b", "ни", corrected, flags=re.IGNORECASE)

            # Правила согласования (очень базовые)
            grammar_rules = {
                r"\bмного\b\s+([а-яё]{2,})ая\b": lambda m: (
                    f"много {m.group(1)[0].lower()}{m.group(1)[1:] if len(m.group(1)) > 1 else ''}"
                ),
                r"\bмного\b\s+([а-яё]{2,})ий\b": lambda m: (
                    f"много {m.group(1)[0].lower()}{m.group(1)[1:] if len(m.group(1)) > 1 else ''}"
                ),
            }

            for pattern, replacement in grammar_rules.items():
                matches = re.findall(pattern, corrected, re.IGNORECASE)
                if matches:
                    corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
                    corrections.append(
                        TextCorrection(
                            original="грамматическая ошибка",
                            corrected="исправлено",
                            type="grammar",
                            language=language,
                            description="Исправлена грамматическая ошибка",
                        )
                    )

        elif language == "en":
            # Английские грамматические правила
            # Subject-verb agreement (очень базовые случаи)
            grammar_patterns = [
                (r"\bhe\b\s+([a-z]{2,})s\b", r"he \1"),  # he run -> he runs
                (r"\bshe\b\s+([a-z]{2,})s\b", r"she \1"),  # she walk -> she walks
                (r"\bit\b\s+([a-z]{2,})\b", r"it \1s"),  # it go -> it goes
            ]

            for pattern, replacement in grammar_patterns:
                matches = re.findall(pattern, corrected, re.IGNORECASE)
                if matches:
                    corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
                    corrections.append(
                        TextCorrection(
                            original="grammar error",
                            corrected="corrected",
                            type="grammar",
                            language=language,
                            description="Fixed grammar error",
                        )
                    )

            # Articles (a/an)
            corrected = re.sub(r"\ba\b\s+([aeiou])", r"an \1", corrected, flags=re.IGNORECASE)
            corrected = re.sub(r"\ban\b\s+([^aeiou\s])", r"a \1", corrected, flags=re.IGNORECASE)

        return corrected, corrections

    def correct_punctuation_and_capitalization(
        self, text: str, language: str
    ) -> tuple[str, list[TextCorrection]]:
        """Исправление пунктуации и регистра"""
        corrections = []
        corrected = text

        if language not in self.language_patterns:
            return corrected, corrections

        patterns = self.language_patterns[language]

        # Применение паттернов пунктуации
        for pattern, replacement in patterns["punctuation_patterns"]:
            old_text = corrected
            corrected = re.sub(pattern, replacement, corrected)

            if old_text != corrected:
                corrections.append(
                    TextCorrection(
                        original="пунктуация",
                        corrected="исправлено",
                        type="punctuation",
                        language=language,
                        description="Исправлена пунктуация",
                    )
                )

        # Исправление регистра
        capital_rules = patterns["capitalization_rules"]

        # Заглавные буквы в начале предложений
        if capital_rules.get("sentence_start"):
            sentences = corrected.split(". ")
            new_sentences = []

            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if sentence and len(sentence) > 0:
                    # Проверяем, что это не сокращение
                    if not any(
                        sentence.lower().startswith(abbrev)
                        for abbrev in capital_rules.get("abbreviations", [])
                    ):
                        if not sentence[0].isupper():
                            sentence = sentence[0].upper() + sentence[1:]

                            if i == 0:
                                corrections.append(
                                    TextCorrection(
                                        original="регистр",
                                        corrected="исправлен",
                                        type="capitalization",
                                        language=language,
                                        description="Добавлена заглавная буква в начале текста",
                                    )
                                )
                            else:
                                corrections.append(
                                    TextCorrection(
                                        original="регистр",
                                        corrected="исправлен",
                                        type="capitalization",
                                        language=language,
                                        description="Добавлены заглавные буквы в начале предложений",
                                    )
                                )

                new_sentences.append(sentence)

            corrected = ". ".join(new_sentences)

        # Добавление точки в конце
        if corrected and corrected[-1] not in ".!?":
            corrected += "."
            corrections.append(
                TextCorrection(
                    original="завершение",
                    corrected="добавлено",
                    type="punctuation",
                    language=language,
                    description="Добавлена точка в конце текста",
                )
            )

        return corrected, corrections

    def get_text_stats(self, text: str, language: str) -> dict[str, int]:
        """Получение статистики текста"""
        char_count = len(text)
        word_count = len(text.split())

        # Подсчет предложений
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        sentence_count = len(sentences)

        # Дополнительная статистика
        if language == "ru":
            vowel_count = len(re.findall(r"[аоеёиуыэюя]", text, re.IGNORECASE))
        elif language == "en":
            vowel_count = len(re.findall(r"[aeiou]", text, re.IGNORECASE))
        else:
            vowel_count = 0

        return {
            "chars": char_count,
            "words": word_count,
            "sentences": sentence_count,
            "vowels": vowel_count,
        }

    def generate_recommendations(
        self, text: str, stats: dict[str, int], language: str, corrections_count: int
    ) -> list[str]:
        """Генерация рекомендаций"""
        recommendations = []

        # Рекомендации по длине
        if stats["words"] < 3:
            if language == "ru":
                recommendations.append("• Текст очень короткий, добавьте больше деталей")
            else:
                recommendations.append("• Text is very short, add more details")
        elif stats["words"] > 100:
            if language == "ru":
                recommendations.append("• Текст длинный, рассмотрите разделение на абзацы")
            else:
                recommendations.append("• Text is long, consider breaking into paragraphs")

        # Рекомендации по предложениям
        if stats["sentences"] == 0:
            if language == "ru":
                recommendations.append("• Добавьте знаки препинания для лучшей читаемости")
            else:
                recommendations.append("• Add punctuation for better readability")
        elif stats["sentences"] == 1 and stats["words"] > 20:
            if language == "ru":
                recommendations.append("• Разделите длинное предложение на несколько коротких")
            else:
                recommendations.append("• Break the long sentence into shorter ones")

        # Рекомендации по качеству
        if corrections_count > 5:
            if language == "ru":
                recommendations.append("• Найдено много ошибок, уделите внимание проверке текста")
            else:
                recommendations.append("• Many errors found, pay attention to text proofreading")
        elif corrections_count == 0:
            if language == "ru":
                recommendations.append("• Отлично! Текст написан грамотно")
            else:
                recommendations.append("• Excellent! Text is well-written")

        # Языковые рекомендации
        if language == "unknown":
            recommendations.append("• Язык текста не определен, проверьте корректность")

        return recommendations[:4]  # Возвращаем до 4 рекомендаций

    def process_text(self, text: str) -> TextAnalysisResult:
        """Полная обработка текста"""
        if not text or not text.strip():
            return TextAnalysisResult(
                original_text=text or "",
                corrected_text=text or "",
                language="unknown",
                corrections=[],
                stats={"chars": 0, "words": 0, "sentences": 0, "vowels": 0},
                recommendations=["• Текст пуст"],
            )

        # Определение языка
        language = self.detect_language(text)

        # Последовательная коррекция
        corrected = text
        all_corrections = []

        # 1. Орфография
        corrected, spell_corrections = self.correct_spelling(corrected, language)
        all_corrections.extend(spell_corrections)

        # 2. Грамматика
        corrected, grammar_corrections = self.correct_grammar(corrected, language)
        all_corrections.extend(grammar_corrections)

        # 3. Пунктуация и регистр
        corrected, punctuation_corrections = self.correct_punctuation_and_capitalization(
            corrected, language
        )
        all_corrections.extend(punctuation_corrections)

        # Статистика
        stats = self.get_text_stats(corrected, language)

        # Рекомендации
        recommendations = self.generate_recommendations(text, stats, language, len(all_corrections))

        return TextAnalysisResult(
            original_text=text,
            corrected_text=corrected,
            language=language,
            corrections=all_corrections,
            stats=stats,
            recommendations=recommendations,
        )
