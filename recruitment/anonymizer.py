import re                        
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

SPACY_MODEL = "en_core_web_md"

_analyzer = None
_anonymizer = None

def _get_engines():
    global _analyzer, _anonymizer
    if _analyzer is None:
        nlp_engine = SpacyNlpEngine(
            models=[{"lang_code": "en", "model_name": SPACY_MODEL}]
        )
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer

def anonymize_text(text: str) -> str:
    # -----------------------------------------------
    # 1. Regex-based pre‑cleaning (emails, phones, URLs)
    # -----------------------------------------------
    cleaned = re.sub(r'\S+@\S+\.\S+', '[EMAIL]', text)
    cleaned = re.sub(r'(\+63|0)[0-9]{9,10}', '[PHONE]', cleaned)
    cleaned = re.sub(
        r'(https?://)?(www\.)?[\w-]+\.(com|org|net|io|dev|me)(/[\w\-\.@]+)*/?',
        '[PROFILE_LINK]',
        cleaned,
        flags=re.IGNORECASE
    )

    # -----------------------------------------------
    # 2. Presidio (names, locations, etc.)
    # -----------------------------------------------
    analyzer, anonymizer = _get_engines()
    results = analyzer.analyze(
        text=cleaned,
        entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION"],
        language="en",
        score_threshold=0.4,
    )
    operators = {
        "PERSON": OperatorConfig("replace", {"new_value": "[CANDIDATE_NAME]"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
        "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
    }
    return anonymizer.anonymize(text=cleaned, analyzer_results=results, operators=operators).text