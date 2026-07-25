"""Prompt templates for title/abstract four-step screening."""

from __future__ import annotations


DISEASE_ALIASES = {
    "cataract": "cataract",
    "amd": "Age-related Macular Degeneration (AMD)",
    "glaucoma": "Glaucoma",
    "drdme": "diabetic retinopathy (DR) or diabetic macular edema/oedema (DME)",
    "rop": "Retinopathy of Prematurity (ROP)",
    "ocularsurface": "ocular surface disease (e.g. dry eye, keratitis, corneal disease, corneal ulcer, conjunctivitis, pterygium, blepharitis, conjunctival disease, meibomian gland dysfunction)",
    "oculomics": "systemic diseases (including diabetes mellitus [DM, diabetes], hypertension [HTN, high blood pressure], cardiovascular disease [CVD], stroke, Alzheimer's disease [AD], dementia, multiple sclerosis [MS], chronic kidney disease [CKD], anemia, lipid disorders, and systemic lupus erythematosus [SLE])",
}


STEP2_PROMPT = """Based on the provided Title and Abstract, determine if the article meets any of the exclusion criteria listed below.

Exclusion Criteria (Step 2):
1. Excluded Article Types:
Reviews, systematic reviews, meta-analyses, conference abstracts, commentaries or opinions, short reports, protocols, white papers, preprints or other grey literature (e.g., editorials, letters, correspondences).

2. Excluded Research Designs or Study Types:
Animal studies (non-human studies), basic science research (e.g., lab-based or mechanistic studies without clinical application), secondary research (research based on previously published data without new primary data collection).

Instructions:
Only judge based on information explicitly stated in the Title and Abstract.
If the article matches any one of the exclusion criteria listed above, mark it for exclusion.
Return only a valid JSON object. Do not add explanation or prefix.

{
  "decision": "True" if not exclude, "False" if exclude,
  "confidence": integer from 0 to 100 indicating your confidence,
  "reason": "A concise explanation summarizing the rationale, referring to key terms or evidence from the title and abstract."
}
"""


STEP3_BASE_PROMPT = """Based on the provided title and abstract, determine whether the article meets the inclusion criteria of primarily focusing on one or more of the following tasks:
Disease diagnosis
Disease classification
Prognosis prediction
Risk prediction

Exclusion Criteria (Step 3):
Articles should be excluded if the main task is NOT one of the four listed above. Examples of tasks to be excluded include image quality assessment, image segmentation tasks without disease-level diagnosis, purely quantitative measurement tasks without diagnosis/classification at disease level, detection of isolated disease signs or features without explicit diagnosis, classification, prognosis, or risk prediction at disease level, treatment planning, surgical assistance, image generation, and dataset construction.

Instructions:
Judge carefully based on the information provided.
If the article clearly focuses on at least one of the four listed tasks, include it.
Clearly identify the main disease(s) studied and main task(s) as keywords.
Return only a valid JSON object. Do not add explanation or prefix.

{
  "decision": "True" if include, "False" if exclude,
  "confidence": integer from 0 to 100 indicating your confidence,
  "reason": "A concise explanation summarizing the rationale, referring to key terms or evidence from the title and abstract.",
  "diseasetype": "string, show the main disease(s) studied",
  "maintasks": "string, the main task(s) of the study (select from: Disease diagnosis, Disease classification, Prognosis prediction, Risk prediction)"
}
"""


STEP3_NOTES = {
    "cataract": """Special Note for Cataract-related articles:
Articles specifically focusing on diagnosis or classification of cataract or its subtypes (e.g., nuclear cataract, cortical cataract, posterior subcapsular cataract, congenital cataract, age-related cataract, cataract severity grading) should be INCLUDED.

Cataract-specific note:
Studies predicting or outputting continuous or categorical severity scores (e.g., LOCS III grading, lens density, opacity indices), without explicit cataract diagnosis or subtype classification, should be EXCLUDED.""",
    "amd": """Special Note for AMD-related articles:
Articles focusing on diagnosis or classification among AMD subtypes (e.g., early AMD, intermediate AMD, late AMD, neovascular AMD, geographic atrophy, wet AMD, dry AMD) should be INCLUDED.

AMD-specific note:
Studies predicting numerical or categorical severity scores (e.g., drusen volume, pigmentary changes, GA area), without explicit AMD disease diagnosis or subtype classification, should be EXCLUDED.""",
    "glaucoma": """Special Note for Glaucoma-related articles:
Articles focusing on diagnosis or classification of glaucoma (e.g., glaucoma vs healthy, POAG vs PACG, early vs moderate vs advanced glaucoma, progression detection) should be INCLUDED.

Glaucoma-specific note:
Studies predicting structural/functional metrics (e.g., RNFL thickness, CDR, VFI, MD) without explicit glaucoma diagnosis, subtype classification, or progression risk assessment should be EXCLUDED.""",
    "drdme": """Special Note for DR/DME-related articles:
Articles focusing on diagnosis or classification among DR or DME stages/subtypes (e.g., no DR, mild NPDR, moderate NPDR, severe NPDR, PDR, presence/absence of DME, focal vs diffuse DME) should be INCLUDED.

DR/DME-specific note:
Studies predicting severity scores or lesion quantities without explicit DR/DME diagnosis or subtype classification should be EXCLUDED.""",
    "rop": """Special Note for ROP-related articles:
Articles specifically focusing on diagnosis/classification between ROP plus disease and ROP pre-plus disease should be INCLUDED.

ROP-specific note:
Studies predicting numerical or categorical severity scores without explicit ROP disease diagnosis or classification (e.g., normal, pre-plus, plus) should be EXCLUDED.""",
    "ocularsurface": """Special Note for Ocular Surface Disease-related articles:
Articles focusing on diagnosis or classification of ocular surface diseases (e.g., dry eye, keratitis, corneal ulcer, meibomian gland dysfunction, pterygium, conjunctivitis, blepharitis, conjunctival disease, corneal opacity subtypes) should be INCLUDED.

Ocular-surface-specific note:
Studies predicting indicators such as TBUT, fluorescein staining grade, gland dropout, or corneal nerve density without explicit diagnosis, subtype classification, or prognosis/risk assessment should be EXCLUDED.""",
    "oculomics": """Special Note for Systemic Disease-related articles:
Articles should be INCLUDED if they focus on diagnosis, classification, prognosis, or risk prediction of systemic diseases, including diabetes, hypertension, cardiovascular disease, stroke, Alzheimer's disease, dementia, multiple sclerosis, chronic kidney disease, anemia, lipid disorders, and systemic lupus erythematosus.

Systemic-disease-specific note:
Studies that only output continuous or categorical scores or biomarker levels without explicit systemic disease diagnosis, subtype classification, or outcome prediction should be EXCLUDED.""",
}


STEP4_PROMPTS = {
    "standard": """Based on the provided title and abstract, determine whether the article meets the criterion of using original medical images (e.g., fundus images, OCT scans, retinal photographs, medical imaging modalities, etc.) as input for the study tasks.

Exclusion Criterion (Step 4):
Exclude articles if they do NOT use original medical images directly as model input. Examples include using numerical measurements, scores, or derived metrics only, or relying solely on clinical, demographic, laboratory, or genetic data without imaging.

Inclusion Criterion:
Clearly INCLUDE if the study directly uses original medical images as model input.
Judge strictly based on explicit evidence.
Return only a valid JSON object. Do not add explanation or prefix.

{
  "decision": "True" if include, "False" if exclude,
  "confidence": integer from 0 to 100 indicating your confidence,
  "reason": "A concise explanation, e.g., Directly uses OCT images / Only uses derived numerical measurements."
}
""",
    "video": """Based on the provided title and abstract, determine whether the article meets the criterion of using original medical images or videos as input for the study tasks.

Exclusion Criterion (Step 4):
Exclude articles if they do NOT use original medical images or video frames directly as model input. Examples include using numerical measurements, scores, or derived metrics only, or relying solely on clinical, demographic, laboratory, or genetic data without imaging.

Inclusion Criterion:
Clearly INCLUDE if the study directly uses original medical images or videos as model input.
Judge strictly based on explicit evidence.
Return only a valid JSON object. Do not add explanation or prefix.

{
  "decision": "True" if include, "False" if exclude,
  "confidence": integer from 0 to 100 indicating your confidence,
  "reason": "A concise explanation, e.g., Directly uses video frames / Only uses derived numerical measurements."
}
""",
    "anterior": """Based on the provided title and abstract, determine whether the article meets the criterion of using original anterior-segment medical images (e.g., AS-OCT, UBM, slit-lamp, anterior segment photograph, gonioscopy) as input for the study tasks.

Exclusion Criterion (Step 4):
Exclude articles if they do NOT use original medical images directly as model input. Examples include using numerical measurements, scores, or derived metrics only, or relying solely on clinical, demographic, laboratory, or genetic data without imaging.

Inclusion Criterion:
Clearly INCLUDE if the study directly uses original anterior-segment medical images as model input.
Judge strictly based on explicit evidence.
Return only a valid JSON object. Do not add explanation or prefix.

{
  "decision": "True" if include, "False" if exclude,
  "confidence": integer from 0 to 100 indicating your confidence,
  "reason": "A concise explanation, e.g., Directly uses AS-OCT images / Uses clinical scores without images."
}
""",
}


def build_step1_prompt(disease_key: str, disease_text: str | None = None) -> str:
    disease = disease_text or DISEASE_ALIASES.get(disease_key.lower(), disease_key)
    return f"""Analyze the following article based on its title and abstract. Determine whether the article is focused on task related to {disease} with artificial intelligence (AI) method.

Criteria for a positive decision (True):
- The article applies or discusses artificial intelligence techniques (e.g., deep learning, artificial neural networks, convolutional neural networks, foundation models, or similar general terms).
- The primary application or focus of the study involves {disease}.

Criteria for a negative decision (False):
- The article does not apply or discuss artificial intelligence techniques.
- The primary application or focus of the study does not involve {disease}.
- The article relies solely on traditional machine learning methods such as support vector machines (SVM), random forests, decision trees, logistic regression, or k-nearest neighbors.

Return only a valid JSON object. Do not add explanation or prefix.

{{
  "decision": "True" or "False",
  "confidence": integer from 0 to 100 indicating your confidence,
  "reason": "A concise explanation summarizing the rationale, referring to key terms or evidence from the title and abstract."
}}
"""


def build_step3_prompt(disease_key: str) -> str:
    note = STEP3_NOTES.get(disease_key.lower(), "")
    if not note:
        return STEP3_BASE_PROMPT
    return STEP3_BASE_PROMPT.replace("Instructions:\n", f"{note}\n\nInstructions:\n")


def get_step4_prompt(kind: str) -> str:
    return STEP4_PROMPTS[kind]

