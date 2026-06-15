# config.py
DB_PATH = "usmle_data.db"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MODEL_QBANK     = "openrouter/free"
MODEL_FLASHCARD = "openrouter/free"

MODELOS_DISPONIVEIS = {
    "🆓 OpenRouter Free (sem créditos)": {
        "qbank": "openrouter/free",
        "flashcard": "openrouter/free",
    },
    "🧠 MiMo v2.5 (requer créditos)": {
        "qbank": "xiaomi/mimo-v2.5-pro",
        "flashcard": "xiaomi/mimo-v2.5",
    },
}

SISTEMAS_DISPONIVEIS = [
    "General_Principles",
    "Microbiology",
    "Cardiovascular",
    "Renal",
    "Endocrine",
    "Neurology",
    "Psychiatry",
    "Pulmonology",
    "Gastroenterology",
    "Hematology",
    "Musculoskeletal",
    "Reproductive_OB_GYN",
    "Dermatology",
    "Ophthalmology",
    "ENT"
]