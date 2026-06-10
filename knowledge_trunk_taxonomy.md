# Knowledge Trunk Taxonomy — Sprint 1.6

## Objetivo

Construir a hierarquia dos **hubs fundamentais ausentes** no grafo de
pré-requisitos antes de adicioná-los. A taxonomia abaixo organiza os
conceitos de Step 1 que devem servir como **tronco** para os conceitos
clínicos de Step 2 já existentes no `prerequisite.json`.

---

## 1. Taxonomy

### Cell Biology
```
Cell Biology
 ├── Cell Membrane
 │    ├── Lipid Bilayer
 │    ├── Membrane Proteins
 │    ├── Ion Channels
 │    │    ├── Voltage-Gated
 │    │    ├── Ligand-Gated
 │    │    └── Mechanically-Gated
 │    └── Transport Mechanisms
 │         ├── Diffusion
 │         ├── Active Transport (Na/K ATPase)
 │         ├── Secondary Active (SGLT)
 │         └── Vesicular Transport
 ├── Signal Transduction
 │    ├── Receptors (GPCR, RTK, Ion Channel)
 │    ├── Second Messengers (cAMP, IP3, Ca2+)
 │    └── Intracellular Cascades (MAPK, JAK-STAT)
 ├── Cell Cycle
 │    ├── G1/S/G2/M Phases
 │    ├── Cyclins / CDKs
 │    ├── Checkpoints
 │    │    ├── G1/S (Rb-p53)
 │    │    └── G2/M
 │    └── Mitosis / Meiosis
 └── Intracellular Organelles
      ├── Mitochondria (OxPhos, Apoptosis)
      ├── ER (Protein Folding, Ca2+)
      ├── Golgi
      ├── Lysosomes
      └── Peroxisomes
```

### Pathology
```
Cell Injury & Death
 ├── Reversible Injury
 │    ├── Cellular Swelling
 │    └── Fatty Change
 ├── Necrosis
 │    ├── Coagulative Necrosis        ← já existe
 │    ├── Liquefactive Necrosis
 │    ├── Caseous Necrosis
 │    ├── Fat Necrosis
 │    └── Gangrenous Necrosis
 └── Apoptosis
      ├── Intrinsic (Mitochondrial)
      ├── Extrinsic (Death Receptor)
      ├── p53 Pathway                  ← já existe como valor
      └── Caspase Cascade


Inflammation
 ├── Acute Inflammation
 │    ├── Vascular Phase
 │    ├── Cellular Phase (Neutrophils)
 │    ├── Chemical Mediators
 │    │    ├── Histamine
 │    │    ├── Prostaglandins
 │    │    ├── Leukotrienes
 │    │    └── Cytokines (IL-1, TNF-α) ← já existem como valores
 │    └── Exudate / Transudate
 ├── Chronic Inflammation
 │    ├── Macrophages / Lymphocytes
 │    ├── Granulomatous Inflammation   ← já existe
 │    ├── Fibrosis                     ← já existe
 │    └── Wound Healing
 │         ├── Primary / Secondary Intention
 │         ├── Granulation Tissue
 │         └── Scar Remodeling
 └── Resolution


Hemodynamics
 ├── Blood Flow / Pressure / Resistance
 │    ├── Cardiac Output               ← já existe
 │    ├── Vascular Resistance
 │    ├── Afterload / Preload          ← já existem
 │    └── Starling Forces              ← já existe
 ├── Edema
 │    ├── Hydrostatic vs Oncotic       ← já existem
 │    ├── Pitting vs Non-Pitting
 │    └── Pulmonary / Peripheral
 ├── Thrombosis
 │    ├── Virchow Triad               ← já existe
 │    ├── Coagulation Cascade
 │    │    ├── Intrinsic Pathway       ← já existe
 │    │    └── Extrinsic Pathway       ← já existe
 │    └── Fibrinolysis                ← já existe
 ├── Embolism
 └── Shock
      ├── Hypovolemic                  ← já existe
      ├── Cardiogenic
      ├── Distributive (Septic)        ← já existe
      └── Obstructive


Ischemia & Hypoxia
 ├── Ischemia → Infarction
 │    ├── Myocardial Infarction        ← já existe
 │    ├── Ischemic Stroke
 │    └── Acute Tubular Necrosis       ← já existe
 └── Hypoxia
      ├── Hypoxemic
      ├── Anemic
      ├── Ischemic
      └── Histiotoxic


Neoplasia
 ├── Carcinogenesis
 │    ├── Initiation (Mutation)
 │    ├── Promotion
 │    └── Progression
 ├── Oncogenes                        ← já existe
 │    ├── Ras, Myc, BCR-ABL           ← já existem
 │    └── Growth Factors
 ├── Tumor Suppressor Genes           ← já existe
 │    ├── p53                         ← já existe
 │    └── Rb                          ← já existe
 ├── Cell Cycle Dysregulation
 ├── DNA Repair Defects
 ├── Angiogenesis
 ├── Metastasis
 └── Paraneoplastic Syndromes        ← já existe
```

### Pharmacology
```
Pharmacology
 ├── Pharmacokinetics (ADME)
 │    ├── Absorption
 │    │    ├── Bioavailability
 │    │    ├── First-Pass Effect
 │    │    └── Routes of Administration
 │    ├── Distribution
 │    │    ├── Volume of Distribution
 │    │    └── Protein Binding
 │    ├── Metabolism
 │    │    ├── Phase I (CYP450)
 │    │    └── Phase II (Conjugation)
 │    └── Elimination
 │         ├── Clearance
 │         ├── Half-Life
 │         └── Renal / Hepatic
 ├── Pharmacodynamics
 │    ├── Drug-Receptor Interactions
 │    │    ├── Agonist / Antagonist
 │    │    ├── Efficacy / Potency
 │    │    └── Dose-Response Curve
 │    ├── Therapeutic Index
 │    └── Tolerance / Dependence
 ├── Autonomic Pharmacology
 │    ├── Cholinergic (Muscarinic, Nicotinic)
 │    └── Adrenergic (Alpha, Beta)
 ├── Antibiotic Mechanisms
 │    ├── Cell Wall / Membrane
 │    ├── Protein Synthesis
 │    ├── Nucleic Acid Synthesis
 │    └── Folate Synthesis
 └── Drug Resistance
```

### Physiology
```
Physiology
 ├── Acid-Base Balance
 │    ├── Buffers (Bicarbonate, Phosphate, Protein)
 │    ├── Respiratory Regulation
 │    ├── Renal Regulation
 │    ├── Anion Gap                     ← já existe
 │    └── Metabolic / Respiratory       ← já existem como valores
 ├── Fluid Compartments (ICF / ECF)
 ├── Membranes & Transport
 │    ├── Diffusion / Osmosis
 │    └── Active Transport
 └── Homeostasis (Feedback Loops)
      ├── RAAS                          ← já existe
      ├── Baroreceptor Reflex           ← já existe
      └── Temperature / Glucose / Ca2+
```

### Immunology
```
Immunology
 ├── Innate Immunity
 │    ├── Barriers (Skin, Mucosa)
 │    ├── Phagocytes (Neutrophils, Macrophages)
 │    ├── Complement System             ← já existe
 │    ├── PRR / TLR
 │    └── NK Cells
 ├── Adaptive Immunity
 │    ├── Humoral (B Cells / Antibodies)
 │    │    ├── Immunoglobulin Classes
 │    │    ├── Somatic Hypermutation
 │    │    └── Class Switching
 │    ├── Cellular (T Cells)
 │    │    ├── CD4+ Helper / CD8+ Cytotoxic
 │    │    ├── MHC Restriction
 │    │    └── T Cell Activation
 │    └── Memory / Tolerance
 ├── Cytokines                          ← valores existem (IL-1, IL-4, etc.)
 │    ├── Interleukins
 │    ├── Interferons
 │    ├── TNF Family
 │    └── Chemokines
 └── Hypersensitivity                  ← já existem tipos II, III, IV
      ├── Type I (IgE / Anaphylaxis)
      ├── Type II (Antibody-Mediated)
      ├── Type III (Immune Complex)
      └── Type IV (Delayed / T Cell)
```

### Genetics
```
Genetics
 ├── DNA Structure & Replication
 │    ├── DNA → RNA → Protein (Central Dogma)
 │    ├── DNA Repair Mechanisms
 │    │    ├── Base Excision Repair
 │    │    ├── Nucleotide Excision Repair
 │    │    ├── Mismatch Repair
 │    │    └── p53 / Apoptosis         ← já existem
 │    └── Telomeres / Senescence
 ├── Transcription & Translation
 │    ├── Gene Expression Regulation
 │    └── Epigenetics (Methylation, Acetylation)
 ├── Mutations
 │    ├── Point (Missense, Nonsense, Silent, Frameshift)
 │    ├── Chromosomal (Aneuploidy, Translocation, Deletion)
 │    └── Trinucleotide Repeats
 └── Inheritance Patterns
      ├── Autosomal Dominant            ← já existe
      ├── Autosomal Recessive           ← já existe
      ├── X-Linked Recessive            ← já existe
      ├── Mitochondrial
      └── Non-Mendelian
           ├── Genomic Imprinting
           ├── Anticipation             ← já existe
           └── Penetrance / Expressivity
```

---

## 2. Coverage Score

Cobertura **semântica real**: quantos conceitos existentes no grafo atual
são descendentes diretos ou indiretos de cada hub candidato.

```
Rank  Hub                       Coverage  Profundidade  Nota
────  ───────────────────────── ────────  ────────────  ─────────────────────
  1   Neoplasia                     25   média 2.4     Cânceres, oncogenes,
                                                        supressores, tumores

  2   Inflammation                  22   média 2.1     Toda "-ite", padrões
                                                        inflamatórios, citocinas

  3   Thrombosis                    11   média 1.8     Coagulação, DIC,
                                                        embolia, Virchow

  4   Cytokines                      7   média 1.0     IL-1/4/5/6, TNF-α
                                                        (já existem como valores)

  5   Hemodynamics                   7   média 1.4     DC, pré/pós-carga,
                                                        Starling, resistência

  6   Cell Injury                    6   média 2.5     Necroses, choque,
                                                        adaptações → profundo

  7   Metabolism                     6   média 1.2     HMP, TCA, ureia,
                                                        purinas, Hb

  8   Hypersensitivity               5   média 1.0     Tipos I-II-III-IV
                                                        (já existem como nós)

  9   Inheritance                    4   média 1.0     AD, AR, XLR, antecipação

 10   Necrosis                       3   média 1.0     Coagulativa, ATN,
                                                        infarto

 11   Acid-Base Balance              2   média 1.0     Anion Gap,
                                                        Acidose Metabólica

 12   Cell Cycle                     2   média 1.0     Rb, p53

 13   Pharmacokinetics               2   média 1.0     Clearance renal,
                                                        absorção de gordura

 14   Shock                          2   média 1.0     Hipovolêmico, séptico

 15   Signal Transduction            2   média 1.0     Receptores nicotínicos,
                                                        fosfatase alcalina
```

---

## 3. Top 10 Prioritários

Critério composto: `Score = coverage × (1 + profundidade × 0.5)`

```
Rank  Hub                       Coverage ×  Depth  Pontuação  Benefício
────  ───────────────────────── ───────────  ────  ────────  ─────────────────
  1   Inflammation                   22      2.1     45      Conecta reumatologia,
                                                                hepatologia, alergia
  2   Neoplasia                      25      2.4     55      Conecta oncologia
                                                                inteira
  3   Cell Injury                     6      2.5     21      Base de TUDO (via
                                                                necrose/infarto/choque)
  4   Hemodynamics                    7      1.4     17      Conecta cardiologia,
                                                                nefrologia, vasculares
  5   Thrombosis                     11      1.8     26      Conecta hemato,
                                                                neurologia, cardio
  6   Cytokines                       7      1.0     14      Conecta imunologia,
                                                                inflamação
  7   Metabolism                      6      1.2     13      Conecta bioquímica
                                                                clínica, erros inatos
  8   Hypersensitivity                5      1.0     10      Já existem como nós
                                                                (menos crítico)
  9   Inheritance                     4      1.0      8      Conecta genética
                                                                clínica
 10   Necrosis                        3      1.0      6      Já parcialmente
                                                                coberto via Cell Injury
```

### Decisão

**Adicionar na Sprint 2** (em ordem):

| # | Hub | Justificativa |
|---|---|---|
| 1 | **Neoplasia** | 25 conceitos conectados. Oncologia inteira pendurada. |
| 2 | **Inflammation** | 22 conceitos conectados. O tronco mais óbvio e mais faltante. |
| 3 | **Thrombosis** | 11 conceitos. Conecta hemato, neuro, cardio. Já tem Virchow Triad como nó, só falta organizar. |
| 4 | **Cell Injury** | Coverage 6 mas profundidade 2.5 — é a âncora de necrose, adaptação, e choque. |
| 5 | **Hemodynamics** | 7 conceitos. Conecta mecânica cardíaca, edema, choque. |

---

## 4. Anexo: Mapeamento Completo

### Neoplasia → conecta 25 conceitos
```
AML (t(15;17) PML-RARA)
Burkitt Lymphoma (t(8;14) Burkitt)
CML (t(9;22) BCR-ABL)
Carcinoid Tumor
Colorectal Cancer
Esophageal Adenocarcinoma
Hepatocellular Carcinoma
Hodgkin Lymphoma
Medullary Thyroid Cancer
Multiple Myeloma
Osteosarcoma
Pancoast Tumor
Prolactinoma
Small Cell Lung Cancer
Squamous Cell Lung Cancer

Oncogenes (Ras, Myc, BCR-ABL)
Tumor Suppressors
Paraneoplastic Syndromes
Metaplasia
p53
Rb Protein
MEN1 / MEN2A
Barrett Esophagus
Lambert-Eaton Syndrome
```

### Inflammation → conecta 22 conceitos
```
Acute Pancreatitis
Alcoholic Hepatitis
Ankylosing Spondylitis
Asthma
Bacterial Meningitis
Cholangitis
Chronic Bronchitis
COPD
Crohn Disease
Dermatomyositis
Dressler Syndrome
Granulomatous Inflammation
Hypersensitivity Pneumonitis
IPF
Nephritic Syndrome
Pericarditis
Polymyositis
Rheumatic Heart Disease
Rheumatoid Arthritis
Sarcoidosis
SLE
Transmural Inflammation
Ulcerative Colitis
```

### Thrombosis → conecta 11 conceitos
```
DIC
Deep Vein Thrombosis
Extrinsic Coagulation Pathway
Factor V Leiden
Fibrinolysis
Intrinsic Coagulation Pathway
Platelet Activation
Pulmonary Embolism
Thrombus Formation
Virchow Triad
vWF
```

### Cell Injury → conecta 6+ (profundidade 2.5)
```
Diretos:
  Coagulative Necrosis
  Acute Tubular Necrosis
  Hypovolemic Shock
  Septic Shock

Indiretos (via Necrosis):
  Myocardial Infarction
  STEMI
  NSTEMI
  Ventricular Free Wall Rupture
  Sickle Cell Disease (Coagulative Necrosis)
  Papillary Muscle Rupture
```

---

## Próximo passo (Sprint 2)

Adicionar os 5 hubs prioritários ao `prerequisite.json` com:
- Seus próprios pré-requisitos (conceitos mais fundamentais)
- Seus dependentes (conceitos já existentes que se conectam)

Exemplo:
```json
{
  "Thrombosis": ["Hemodynamics", "Coagulation Cascade", "Endothelial Injury"],
  "Deep Vein Thrombosis": ["Thrombosis", "Virchow Triad"],
  "Pulmonary Embolism": ["Thrombosis", "Deep Vein Thrombosis"]
}
```

Isso transforma o grafo de uma ontologia Step 2 plana para uma ontologia
Step 1 → Step 2 hierárquica, aumentando profundidade e poder preditivo.
