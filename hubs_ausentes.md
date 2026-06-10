# Hubs Ausentes — Sprint 1.5

## Metodologia

Analisados 114 conceitos-chave e 368 nós totais do `prerequisite.json`.
Identificados mecanismos fundamentais que **não existem como nós explícitos** mas são
implicitamente necessários como pré-requisitos de múltiplas doenças.

Critérios:
- **Alto poder explicativo** — o conceito explica o mecanismo de ≥3 doenças
- **Implicitamente referenciado** — já existe via conceitos específicos (ex: `Coagulative Necrosis` existe, `Necrosis` não)
- **Ausência total** — não aparece nem como key nem como value no JSON

---

## Patologia — 12 conceitos faltando

| Conceito | Evidência | Doenças que dependem |
|---|---|---|
| `Cell Injury` | Núcleo da patologia | Todas (isquemia, toxinas, trauma) |
| `Necrosis` | Só existe `Coagulative Necrosis`, `Acute Tubular Necrosis` | STEMI, ATN, DIC, Pancreatitis |
| `Apoptosis` | Ausente (mecanismo oposto à necrose) | Câncer, neurodegeneração, desenvolvimento |
| `Inflammation` | Só existe `Chronic Inflammation`, `Transmural Inflammation`, `Granulomatous Inflammation` | Toda doença inflamatória |
| `Wound Healing` | Ausente | Cirurgia, feridas, fibrose |
| `Ischemia` | Ausente | IAM, AVC, DAP, ATN |
| `Hypoxia` | Ausente | Todas as doenças respiratórias/cardíacas |
| `Edema` | Só existe `Papilledema` | ICC, cirrose, renal, inflamação |
| `Thrombosis` | Só existe `Deep Vein Thrombosis`, `Virchow Triad` | IAM, AVC, PE, DIC |
| `Embolism` | Só existe `Pulmonary Embolism` | PE, AVC, IAM |
| `Shock` | Só existe `Septic Shock`, `Hypovolemic Shock` | Sepse, trauma, ICC |
| `Neoplasia` | Só existe `Paraneoplastic Syndromes` | Todos os cânceres |

### Efeito dominó esperado
```
Cell Injury
 ├── Necrosis          → Coagulative Necrosis → STEMI
 ├── Apoptosis         → p53, Rb → Osteosarcoma
 ├── Inflammation      → Chronic/Granulomatous → Crohn, Sarcoidosis
 └── Metaplasia        → Barrett → Esophageal Adenocarcinoma
```

---

## Farmacologia — 8 conceitos faltando

| Conceito | Evidência | Por que é necessário |
|---|---|---|
| `Pharmacokinetics` | Ausente — nenhum conceito de ADME existe | Base para entender qualquer fármaco |
| `Pharmacodynamics` | Ausente — nenhum conceito de receptor/efeito | Base para mecanismo de ação |
| `Drug Metabolism` | Ausente — `Cytochrome P450` não existe | Interações, polifarmácia, hepatotoxicidade |
| `Drug Receptors` | Ausente — agonista/antagonista não existe | Todos os mecanismos farmacológicos |
| `Autonomic Pharmacology` | Ausente | Simpático/parassimpático → 50% das drogas |
| `Antibiotic Mechanisms` | Ausente | Todas as infecções bacterianas |
| `Drug Resistance` | Ausente | TB, MRSA, HIV, quimioterapia |
| `Therapeutic Index` | Ausente | Warfarina, lítio, digoxina, aminoglicosídeos |

### Observação
Farmacologia é o **buraco negro** da ontologia. Não há um único conceito farmacológico
como nó explícito. Medicamentos específicos (`Class IA Antiarrhythmics`, `NSAID-Induced Ulcer`)
aparecem como valores, mas sem camada geral de farmacologia.

---

## Fisiologia — 10 conceitos faltando

| Conceito | Evidência | Por que é necessário |
|---|---|---|
| `Cell Membrane` | Ausente | Fluxo iônico, potencial de ação, receptores |
| `Ion Channels` | Ausente | PA cardíaco/neuronal, canalopatias |
| `Signal Transduction` | Ausente | Receptores → cascatas → efeito celular |
| `Homeostasis` | Ausente | Feedback loops, equilíbrio ácido-base, temperatura |
| `Acid-Base Balance` | Só existe `Metabolic Acidosis`, `Anion Gap` | Toda gasometria, DKA, RTA, insuficiência renal |
| `Hemodynamics` | Ausente | Fluxo, pressão, resistência, DC |
| `Oxygen Transport` | Ausente | Hemoglobina, curva de dissociação, hipóxia |
| `Fluid Compartments` | Ausente | LIC/LEC, edema, desidratação, choque |
| `Membrane Transport` | Ausente | SGLT, Na/K ATPase, canais, carreadores |
| `Action Potential` | Só existe `Cardiac Action Potential` | Neurofisiologia, cardiologia, musculatura |

### Observação
`Cardiac Action Potential` existe mas `Action Potential` geral (neuronal, muscular) não.
`Anion Gap` existe mas `Acid-Base Balance` não.
`RAAS`, `Aldosterone`, `Baroreceptor Reflex` existem mas `Homeostasis` ou `Feedback Loops` não.

---

## Genética — 6 conceitos faltando (os mais críticos)

| Conceito | Evidência | Por que é necessário |
|---|---|---|
| `DNA Structure` | Ausente | Mutações, reparo, replicação |
| `DNA Repair` | `p53` existe como value mas `DNA Repair` não | Câncer (BRCA, MSH, p53) |
| `Transcription` | Ausente | Regulação gênica, oncogenes, signaling |
| `Translation` | Ausente | Síntese proteica, antibióticos |
| `Cell Cycle` | `Rb Protein` existe value mas `Cell Cycle` não | Ciclo celular, câncer, quimioterapia |
| `Mutation` | Ausente — nenhum tipo de mutação existe | Carcinogênese, doenças genéticas |

### Observação
`Autosomal Dominant Inheritance` e `X-Linked Recessive` existem como valores,
mas a camada molecular (DNA → RNA → proteína → mutação → fenótipo) é completamente ausente.
`Oncogenes` e `Tumor Suppressors` existem como valores mas `Cell Cycle`, `DNA Repair`, e `Apoptosis` (que os conectam biologicamente) não.

---

## Imunologia — 5 conceitos faltando (os mais críticos)

| Conceito | Evidência | Por que é necessário |
|---|---|---|
| `Innate Immunity` | Ausente | Barreiras, fagócitos, complemento, PRR |
| `Adaptive Immunity` | Ausente | LB, LT, MHC, memória, tolerância |
| `Cytokines` | Ausente — `IL-1`, `IL-4`, `IL-5`, `IL-6`, `TNF-alpha` existem como values mas `Cytokines` não | Toda imunologia |
| `MHC` | Ausente | Apresentação antigênica, transplante, autoimunidade |
| `Antigen Presentation` | Ausente | Rejeição, hipersensibilidade tardia, imunidade tumoral |

### Observação
A imunologia é a área **mais paradoxal** da ontologia:
- `Autoimmunity Mechanisms` é o nó mais conectado (11 dependentes)
- `Type II/III/IV Hypersensitivity` existem como categorias
- `IL-1`, `IL-4`, `IL-5`, `IL-6`, `TNF-alpha`, `IgA`, `IgE` existem como valores específicos
- Mas `Cytokines`, `Innate Immunity`, `Adaptive Immunity`, `MHC`, `Antibody`, `Antigen` **não existem**

Ou seja: os galhos e folhas estão lá, mas o tronco não.

---

## Resumo — Lista Prioritária (25 hubs para adicionar)

```
## PATOLOGIA (7)
Cell Injury
Necrosis
Apoptosis
Inflammation
Wound Healing
Ischemia
Neoplasia

## FARMACOLOGIA (5)
Pharmacokinetics
Pharmacodynamics
Drug Metabolism
Autonomic Pharmacology
Antibiotic Mechanisms

## FISIOLOGIA (5)
Cell Membrane
Ion Channels
Signal Transduction
Hemodynamics
Acid-Base Balance

## GENÉTICA (4)
DNA Repair
Cell Cycle
Transcription
Mutation

## IMUNOLOGIA (4)
Innate Immunity
Adaptive Immunity
Cytokines
MHC

Total: 25 novos conceitos
```

---

## Próximo passo

Para cada um desses 25 conceitos, definir seus pré-requisitos (para integrá-los
como nós no grafo) e suas dependências (ligá-los aos conceitos específicos já existentes).

Exemplo para `Necrosis`:
```json
{
  "Necrosis": ["Cell Injury", "Ischemia", "ATP Depletion"],
  "Coagulative Necrosis": ["Necrosis", "Hypoxia", "Lactic Acidosis"],
  "Liquefactive Necrosis": ["Necrosis", "Neutrophils", "Proteolytic Enzymes"],
  "Caseous Necrosis": ["Necrosis", "Macrophages", "Mycobacterium tuberculosis"],
  "Fat Necrosis": ["Necrosis", "Lipase", "Free Fatty Acids"]
}
```

Isso transforma um nó folha existente (`Coagulative Necrosis`, que hoje é raiz)
em parte de uma hierarquia, aumentando a profundidade e o poder preditivo do grafo.
