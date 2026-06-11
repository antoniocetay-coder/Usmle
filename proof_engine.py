import json
import streamlit as st
import random
from ai_client import chat_json
from config import MODEL_QBANK
from ai_engine import TAXONOMIA_COMPLETA, limpar_json
from mastery import DIFFICULTY_RANK


def _get_prereqs_and_related(tag_alvo):
    prereqs = []
    related = []
    try:
        with open("prerequisite.json", "r", encoding="utf-8") as f:
            prereq_data = json.load(f)
        prereqs = prereq_data.get(tag_alvo, [])
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    sistemas = list(TAXONOMIA_COMPLETA.keys())
    random.shuffle(sistemas)
    collected = []
    for sis in sistemas:
        for disc, tags in TAXONOMIA_COMPLETA[sis].items():
            if isinstance(tags, list) and tag_alvo in tags:
                for t in tags:
                    if t != tag_alvo and t not in prereqs and t not in collected:
                        collected.append(t)
        if len(collected) >= 5:
            break

    if not related and collected:
        related = collected[:3]

    return prereqs[:5], related[:3]


def _get_confusions(tag_alvo):
    try:
        from database import get_top_confounders
        return get_top_confounders(tag_alvo, limit=5)
    except Exception:
        return []


def gerar_prompt_prova(tag_alvo, dificuldade_media, prereqs, related, confusions):
    cog_order_map = {
        0: "1st Order (Direct Recall / Diagnosis)",
        1: "2nd Order (Pathophysiology / Next Step)",
        2: "3rd Order (Integrated Reasoning / Complications)",
    }

    prereq_text = ", ".join(prereqs) if prereqs else "None (foundational)"
    related_text = ", ".join(related) if related else "None"
    confusions_text = ", ".join(confusions) if confusions else "None"

    ex_distribution = (
        "2 Easy (1st Order)\n"
        "6 Medium (1st or 2nd Order)\n"
        "8 Hard (2nd Order minimum)\n"
        "4 Insane (3rd Order required)"
    )

    return f"""
PURPOSE: VALIDATION EXAM — HARD MODE

The student claims mastery of "{tag_alvo}" (estimated Real Knowledge: {dificuldade_media:.0%}).
This 20-question exam will CONFIRM or REFUTE that claim.
If they pass (>=16/20), the tag receives PROVEN status.
If they fail, it is locked for 7 days.

MANDATORY DISTRIBUTION:
- 12 questions directly about: {tag_alvo}
- 5 questions about PREREQUISITES: {prereq_text}
- 3 questions about RELATED concepts: {related_text}

DIFFICULTY BREAKDOWN (MANDATORY — generate EXACTLY these counts):
{ex_distribution}

Each question object MUST include fields: "difficulty", "cognitive_order".

KNOWN CONFUSIONS (use these as distractors where applicable):
{confusions_text}

RETURN FORMAT (valid JSON only):
{{
  "validation_exam": {{
    "target_tag": "{tag_alvo}",
    "questions": [
      {{
        "vignette": "clinical scenario...",
        "options": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
        "correct": "A",
        "explanations": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
        "educational_objective": "...",
        "content_tags": ["{tag_alvo}", ...],
        "difficulty": "Hard",
        "cognitive_order": "2nd Order (Pathophysiology / Next Step)"
      }}
    ]
  }}
}}
"""


def gerar_prova(tag_alvo, api_key, num_questoes=20):
    prereqs, related = _get_prereqs_and_related(tag_alvo)
    confusions = _get_confusions(tag_alvo)

    prompt = gerar_prompt_prova(tag_alvo, 0.0, prereqs, related, confusions)

    try:
        texto_bruto = chat_json(prompt, MODEL_QBANK, api_key, temperature=0.4, reasoning=False)
        texto = limpar_json(texto_bruto)
        if not texto:
            return []

        dados = json.loads(texto)
        questoes = dados.get("validation_exam", {}).get("questions", [])

        validadas = []
        for q in questoes:
            if all(k in q for k in ("vignette", "options", "correct", "difficulty")):
                q["correct"] = q["correct"].strip().upper()[0]
                validadas.append(q)

        return validadas[:num_questoes]

    except Exception as e:
        st.error(f"⚠️ Erro ao gerar prova de validação: {str(e)}")
        return []
