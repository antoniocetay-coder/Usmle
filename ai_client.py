"""Cliente HTTP único para OpenRouter.

Centraliza todas as chamadas ao endpoint /chat/completions para evitar
repetição de boilerplate nos call sites. Suporta o flag `reasoning`
usado pelos modelos Xiaomi MiMo.
"""

import json
import requests
from config import OPENROUTER_BASE_URL


def _post(messages, model, api_key, temperature=0.4, reasoning=False):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if reasoning:
        payload["reasoning"] = {"enabled": True}

    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]


def _extract_content(msg):
    """Extrai o conteúdo da resposta, lidando com reasoning models.

    Modelos com reasoning podem retornar o conteúdo final em 'content'
    ou em 'reasoning_details'. Alguns colocam tudo em 'reasoning_details'
    e deixam 'content' vazio.
    """
    content = msg.get("content") or ""

    if content.strip():
        return content

    # Fallback: reasoning_details pode conter o JSON final
    details = msg.get("reasoning_details") or ""
    if isinstance(details, list):
        # Alguns modelos retornam como lista de blocos
        parts = []
        for block in details:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(str(block))
        details = "\n".join(parts)

    if details.strip():
        return details

    return ""


def chat_text(prompt, model, api_key, temperature=0.4, reasoning=False):
    """Retorna o conteúdo textual da resposta."""
    msg = _post(
        [{"role": "user", "content": prompt}],
        model, api_key, temperature, reasoning,
    )
    return _extract_content(msg)


def chat_json(prompt, model, api_key, temperature=0.4, reasoning=False):
    """Retorna string crua; limpar_json() cuida de blocos ```json```."""
    return chat_text(prompt, model, api_key, temperature, reasoning)
