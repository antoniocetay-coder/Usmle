from taxonomy import TAGS_GLOBAIS_PERMITIDAS


import re

def limpar_json(texto: str) -> str:
    if not texto:
        return ""

    # Remove blocos <think>...</think> (DeepSeek R1, QwQ, etc.)
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL)

    # Remove blocos ```json ... ``` ou ``` ... ```
    texto = re.sub(r"```(?:json)?\s*", "", texto)
    texto = re.sub(r"```", "", texto)

    texto = texto.strip()

    # Extrai o primeiro objeto JSON válido { ... }
    start = texto.find("{")
    if start == -1:
        return ""

    depth = 0
    for i, ch in enumerate(texto[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return texto[start:i+1]

    return ""


SCHEMA_OBRIGATORIO = {
    "vignette",
    "options",
    "correct",
    "explanations",
    "educational_objective",
    "content_tags",
    "distractor_tags",
}


def validar_questao(q, sistema):
    if not isinstance(q, dict):
        return False, "A IA não devolveu um formato de dicionário válido."

    faltando = SCHEMA_OBRIGATORIO - q.keys()
    if faltando:
        return False, f"Faltam informações no JSON gerado: {faltando}"

    tags_geradas = q.get("content_tags", [])
    if not tags_geradas:
        return False, "A IA não gerou nenhuma Tag para a questão."

    if TAGS_GLOBAIS_PERMITIDAS:
        invalid_tags = [t for t in tags_geradas if t not in TAGS_GLOBAIS_PERMITIDAS]
        if invalid_tags:
            return False, f"Alucinação nas content_tags: {invalid_tags}"

        dist_tags = q.get("distractor_tags", {})
        for letra, tag in dist_tags.items():
            if tag not in TAGS_GLOBAIS_PERMITIDAS:
                return False, f"Alucinação no distrator {letra}: '{tag}'"

    return True, "OK"
