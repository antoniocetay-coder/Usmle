import os
import random
import json
from dataclasses import dataclass, field as dc_field

from config import SISTEMAS_DISPONIVEIS
from database import (
    get_tags_em_cooldown, salvar_questao, registrar_cooldown_tags
)
from analytics import get_tag_stats
from mastery import (
    classify_tag_bkt, real_knowledge, get_next_level,
    DIFFICULTY_RANK, COGNITIVE_RANK, P_L0,
    RANK_TO_DIFFICULTY, RANK_TO_COGNITIVE
)
from ai_engine import TAXONOMIA_COMPLETA
from database import get_tags_proven


# ---------------------------------------------------------------------------
# Pré-requisitos (Knowledge Graph)
# ---------------------------------------------------------------------------
def _carregar_prerequisites():
    path = os.path.join(os.path.dirname(__file__), "prerequisite.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

PREREQUISITES = _carregar_prerequisites()


# ---------------------------------------------------------------------------
# Estruturas de dados públicas
# ---------------------------------------------------------------------------
@dataclass
class TagSuggestion:
    tag: str
    sistema: str
    rk: float
    next_difficulty: str
    next_cognitive: str

@dataclass
class StudyPath:
    id: str
    titulo: str
    descricao: str
    emoji: str
    tags: list
    dificuldade: str
    ordem_cognitiva: str


# ---------------------------------------------------------------------------
# Student Brain
# ---------------------------------------------------------------------------
class StudentBrain:

    def __init__(self):
        self._stats = {}
        self._proven = set()
        self._cooldown = set()
        self._stale = True

    # ── refresh ──────────────────────────────────────────────────────────
    def refresh(self):
        self._stats = get_tag_stats()
        self._proven = get_tags_proven()
        self._cooldown = set(get_tags_em_cooldown(horas=48))
        self._stale = False

    # ── helpers internos ─────────────────────────────────────────────────
    def _get_sistema_for_tag(self, tag):
        for sis, disciplinas in TAXONOMIA_COMPLETA.items():
            for tags_lista in disciplinas.values():
                if isinstance(tags_lista, list) and tag in tags_lista:
                    return sis
        return "General_Principles"

    def _enrich(self, tag):
        s = self._stats.get(tag, {"correct": 0, "total": 0, "mastery_prob": P_L0,
                                   "max_difficulty": "Easy",
                                   "max_cognitive_order": "1st Order (Direct Recall / Diagnosis)"})
        prob = s.get("mastery_prob", P_L0)
        if prob is None:
            prob = P_L0
        rk = real_knowledge(prob, s.get("max_difficulty", "Easy"),
                            s.get("max_cognitive_order", "1st Order (Direct Recall / Diagnosis)"))
        next_d, next_c = get_next_level(rk)
        return prob, rk, next_d, next_c

    def _interceptar_prereqs(self, tags_alvo):
        tags_finais = []
        for tag in tags_alvo:
            prereqs = PREREQUISITES.get(tag, [])
            foi_substituida = False
            for prereq in prereqs:
                s = self._stats.get(prereq, {"correct": 0, "total": 0, "mastery_prob": 0.15})
                prob = s.get("mastery_prob")
                if prob is None:
                    prob = 0.15
                if prob < 0.65:
                    if prereq not in tags_finais:
                        tags_finais.append(prereq)
                    foi_substituida = True
                    break
            if not foi_substituida and tag not in tags_finais:
                tags_finais.append(tag)
        return tags_finais

    def _resolve_sistema(self, tags):
        sistemas = [self._get_sistema_for_tag(t) for t in tags]
        return max(set(sistemas), key=sistemas.count) if sistemas else "General_Principles"

    def _filter_cooldown(self, tags):
        disponiveis = [t for t in tags if t not in self._cooldown]
        return disponiveis if disponiveis else tags

    def _make_tag_suggestion(self, tag):
        _, rk, next_d, next_c = self._enrich(tag)
        return {
            "tag": tag,
            "sistema": self._get_sistema_for_tag(tag),
            "rk": round(rk, 2),
            "next_difficulty": next_d,
            "next_cognitive": next_c,
        }

    # ── construção dos 3 caminhos ────────────────────────────────────────
    def _build_review(self):
        criticas = sorted(
            [t for t in self._stats if t not in self._proven],
            key=lambda t: (self._enrich(t)[1], t)
        )
        criticas = [t for t in criticas if self._enrich(t)[1] < 0.50]
        criticas = self._interceptar_prereqs(criticas)
        criticas = self._filter_cooldown(criticas)

        tags = []
        for tag in criticas:
            if len(tags) >= 5:
                break
            tags.append(self._make_tag_suggestion(tag))

        if len(tags) < 2:
            fallback = sorted(
                [t for t in self._stats if t not in self._proven],
                key=lambda t: self._enrich(t)[1]
            )
            for tag in fallback:
                if len(tags) >= 2:
                    break
                tags.append(self._make_tag_suggestion(tag))

        if not tags:
            sistemas = random.sample(SISTEMAS_DISPONIVEIS, min(2, len(SISTEMAS_DISPONIVEIS)))
            for s in sistemas:
                tags.append({
                    "tag": s, "sistema": s, "rk": 0.0,
                    "next_difficulty": "Medium", "next_cognitive": "1st Order (Direct Recall / Diagnosis)",
                })

        return StudyPath(
            id="review",
            titulo="Revisar Lacunas",
            descricao="Fortaleça fundamentos com RK < 50%",
            emoji="🔴",
            tags=tags,
            dificuldade="Medium",
            ordem_cognitiva="1st Order (Direct Recall / Diagnosis)",
        )

    def _build_advance(self):
        candidatas = sorted(
            [t for t in self._stats if t not in self._proven],
            key=lambda t: self._enrich(t)[1]
        )
        candidatas = [t for t in candidatas if 0.50 <= self._enrich(t)[1] < 0.85]
        candidatas = self._interceptar_prereqs(candidatas)
        candidatas = self._filter_cooldown(candidatas)

        tags = []
        for tag in candidatas:
            if len(tags) >= 5:
                break
            tags.append(self._make_tag_suggestion(tag))

        if len(tags) < 2:
            ampliado = sorted(
                [t for t in self._stats if t not in self._proven],
                key=lambda t: self._enrich(t)[1]
            )
            ampliado = [t for t in ampliado if 0.40 <= self._enrich(t)[1] < 0.85]
            for tag in ampliado:
                if len(tags) >= 2:
                    break
                tags.append(self._make_tag_suggestion(tag))

        if not tags:
            for _ in range(2):
                tags.append({
                    "tag": random.choice(SISTEMAS_DISPONIVEIS),
                    "sistema": SISTEMAS_DISPONIVEIS[0], "rk": 0.50,
                    "next_difficulty": "Medium", "next_cognitive": "1st Order (Direct Recall / Diagnosis)",
                })

        max_diff_rank = max(DIFFICULTY_RANK.get(t["next_difficulty"], 0) for t in tags)
        max_cog_rank = max(
            COGNITIVE_RANK.get(t.get("next_cognitive",
                                     "1st Order (Direct Recall / Diagnosis)"), 0)
            for t in tags
        )

        return StudyPath(
            id="advance",
            titulo="Avançar Mastery",
            descricao="Eleve o nível de tags em desenvolvimento",
            emoji="🟡",
            tags=tags,
            dificuldade=RANK_TO_DIFFICULTY.get(max_diff_rank, "Hard"),
            ordem_cognitiva=RANK_TO_COGNITIVE.get(max_cog_rank, "2nd Order (Pathophysiology / Next Step)"),
        )

    def _build_expand(self):
        vistas = set()
        for tag in self._stats:
            s = self._stats[tag]
            prob = s.get("mastery_prob", P_L0)
            if prob is None:
                prob = P_L0
            if prob > P_L0:
                vistas.add(tag)

        todas_tags = set()
        sistema_to_tags = {}
        for sis, disciplinas in TAXONOMIA_COMPLETA.items():
            sistema_to_tags[sis] = []
            for tags_lista in disciplinas.values():
                if isinstance(tags_lista, list):
                    sistema_to_tags[sis].extend(tags_lista)
                    todas_tags.update(tags_lista)

        novas = sorted(
            [t for t in todas_tags if t not in vistas and t not in self._proven],
            key=lambda t: self._get_sistema_for_tag(t)
        )
        novas = self._filter_cooldown(novas)

        seen_sistemas = set()
        tags = []
        for tag in novas:
            sis = self._get_sistema_for_tag(tag)
            if sis not in seen_sistemas or len(tags) < 2:
                seen_sistemas.add(sis)
                tags.append(self._make_tag_suggestion(tag))
            if len(tags) >= 5:
                break

        if len(tags) < 2:
            sistemas_com_menos = sorted(
                SISTEMAS_DISPONIVEIS,
                key=lambda s: sum(1 for t in sistema_to_tags.get(s, []) if t in vistas)
            )
            for sis in sistemas_com_menos:
                if len(tags) >= 2:
                    break
                pool = [t for t in sistema_to_tags.get(sis, []) if t not in vistas]
                if pool:
                    tag = random.choice(pool)
                    tags.append({
                        "tag": tag, "sistema": sis, "rk": 0.0,
                        "next_difficulty": "Easy", "next_cognitive": "1st Order (Direct Recall / Diagnosis)",
                    })

        if not tags:
            for sis in random.sample(SISTEMAS_DISPONIVEIS, min(2, len(SISTEMAS_DISPONIVEIS))):
                tags.append({
                    "tag": sis, "sistema": sis, "rk": 0.0,
                    "next_difficulty": "Easy", "next_cognitive": "1st Order (Direct Recall / Diagnosis)",
                })

        return StudyPath(
            id="expand",
            titulo="Expandir Áreas",
            descricao="Explore tópicos novos ou pouco vistos",
            emoji="🟢",
            tags=tags,
            dificuldade="Easy",
            ordem_cognitiva="1st Order (Direct Recall / Diagnosis)",
        )

    # ── API pública ──────────────────────────────────────────────────────
    def get_paths(self):
        if self._stale:
            self.refresh()
        return [
            self._build_review(),
            self._build_advance(),
            self._build_expand(),
        ]

    def execute(self, path_id, qtd, api_key):
        if self._stale:
            self.refresh()

        paths = self.get_paths()
        path = next((p for p in paths if p.id == path_id), paths[0])

        tags_alvo = [t["tag"] for t in path.tags[:qtd]]
        if not tags_alvo:
            return 0

        sistema = self._resolve_sistema(tags_alvo)

        from ai_engine import gerar_lote_questoes

        MAX_POR_CALL = 5
        sucessos = 0

        for start in range(0, len(tags_alvo), MAX_POR_CALL):
            chunk = tags_alvo[start:start + MAX_POR_CALL]
            questoes = gerar_lote_questoes(
                sistema, path.dificuldade, path.ordem_cognitiva,
                api_key, chunk, len(chunk)
            )
            for q in questoes:
                salvar_questao(sistema, path.dificuldade, q, acertou=False,
                               tags=q["content_tags"], status="pending",
                               cognitive_order=path.ordem_cognitiva)
                registrar_cooldown_tags(q["content_tags"])
                sucessos += 1

        return sucessos

    def get_tag_state(self, tag):
        _, rk, next_d, next_c = self._enrich(tag)
        return {
            "tag": tag,
            "sistema": self._get_sistema_for_tag(tag),
            "rk": round(rk, 2),
            "proven": tag in self._proven,
            "next_difficulty": next_d,
            "next_cognitive": next_c,
        }
