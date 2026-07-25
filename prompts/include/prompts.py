"""Prompts for full-text external-validation assessment.

This stage follows the manuscript method: full-text assessment of included
studies to determine external validation, real-world validation, prospective
validation, and RCT status.
"""

STEP1_BASIC_INFO_PROMPT = """You are an expert scientific information extractor.
Extract basic study information from the full text, including tables, figures,
and supplementary sections when available. Output ONLY valid JSON.

STRICT RULES
1) Evidence-first: only fill a field if the paper explicitly states it. If not explicit, use "Not reported".
2) Do NOT infer countries, model names, supervision type, or label type from common knowledge.
3) If multiple candidate answers exist, choose the most specific one and explain uncertainty in extraction_notes.

Required fields:
- title: full paper title.
- authors: all authors.
- first_author_country: country of the first author's primary affiliation.
- last_corresponding_author_country: country of the last corresponding author's primary affiliation. If corresponding author is absent, use the last author's affiliation and note this.
- method: use "[Category] [Specific Structure]". Categories: Foundation model / Traditional Deep Learning / LLM.
- task_objective: disease-task description, e.g. "DR-screening and diagnosis", "AMD-prognosis".
- data_modality: model input modalities, using abbreviations when possible, e.g. CFP, OCT, AS-OCT, OCTA, FAF, FFA, ICGA, UWF, slit lamp, video.
- diagnosed_diseases: target ophthalmic or systemic diseases.
- supervision_type: Supervised, Unsupervised, Semi-supervised, Self-supervised, or Not reported.
- validation_strategy: e.g. k-fold cross-validation, random split, fixed test set.
- classification_type: Single-label, Multi-label, Multi-class, or Not reported.

Return this JSON schema exactly:
{
  "title": "",
  "authors": [],
  "first_author_country": "",
  "last_corresponding_author_country": "",
  "method": "",
  "task_objective": [],
  "data_modality": [],
  "diagnosed_diseases": [],
  "supervision_type": "",
  "validation_strategy": "",
  "classification_type": "",
  "extraction_notes": {
    "reasoning": ""
  }
}
"""

STEP2_EXTERNAL_EVIDENCE_PROMPT = """You are an expert reviewer for TRIPOD+AI-style external validation assessment.
Extract all model development and validation dataset evidence from the full text.
Then strictly determine whether each dataset is development/internal validation
or external validation.

EXTERNAL VALIDATION DECISION RULES
A dataset is external validation ONLY IF all conditions are met:
1) It is evaluated as an independent test/validation cohort; AND
2) It originates from at least one of the following:
   - a different hospital, clinic system, country, or geographic region;
   - a different registry, database, or data-collection system;
   - a distinct public repository not used for model training/development; AND
3) Performance metrics are explicitly reported for that external dataset.

NOT external validation:
- random split from the same dataset, including 80/20 split;
- cross-validation folds from the same dataset;
- same registry, institution, or database with only resampling or repartitioning;
- temporal split alone, unless the authors explicitly state it is an independent external cohort;
- data source not clearly described or lacking explicit independence;
- performance metrics not separated by dataset, or only reported for training/internal validation.


Required output:
{
  "datasets_evidence": [
    {
      "dataset_name": "",
      "dataset_description": "short verbatim or near-verbatim evidence from the paper",
      "dataset_type": "development/internal validation/external validation",
      "dataset_source": "",
      "dataset_country": "",
      "dataset_modality": "",
      "population_country": "",
      "sample_size_evidence": "subjects/eyes/images evidence or Not reported",
      "metrics_list": [
        {"metric": "AUC/ACC/SEN/SPE/PPV/F1/KAPPA/other", "value": "", "text": "", "location": "Page/Table/Figure"}
      ],
      "location": "Page X, Table Y, Figure Z, or section name"
    }
  ]
}

Output ONLY valid JSON. Do not include markdown or commentary.
"""

STEP3_FINAL_DECISION_PROMPT = """You are a senior researcher verifying full-text evidence.
Using Step 1 basic information and Step 2 dataset evidence, produce the final
study-level external-validation decision and structured dataset table.

STUDY-LEVEL RULES
- external_validation: "Yes" ONLY if at least one dataset in Step 2 has dataset_type == "external validation". Otherwise "No".


CONSISTENCY CHECKS
1) Keep Step 1 fields unless Step 2 evidence clearly contradicts them.
2) Every final dataset must be derived from Step 2 datasets_evidence.
3) Metrics must use uppercase metric names.
4) Convert percentage values to decimals between 0 and 1 when possible, e.g. 98.7% -> 0.987.
5) If external_validation is "Yes", name at least one external validation dataset in extraction_notes.reasoning.

Return this JSON schema exactly:
{
  "title": "",
  "authors": [],
  "first_author_country": "",
  "last_corresponding_author_country": "",
  "method": "",
  "task_objective": [],
  "data_modality": [],
  "diagnosed_diseases": [],
  "supervision_type": "",
  "validation_strategy": "",
  "classification_type": "",
  "external_validation": "Yes/No",
  "extraction_notes": {
    "reasoning": ""
  },
  "datasets": [
    {
      "type": "development/internal validation/external validation",
      "name": "",
      "modality": "",
      "source": "",
      "country": "",
      "prospective": "Yes/No/NA",
      "population_country": "",
      "count": {
        "subjects": "Not reported",
        "eyes": "Not reported",
        "images": "Not reported"
      },
      "evaluation_metrics": [
        {
          "metric_name": "",
          "value": "",
          "original_text": "",
          "location": ""
        }
      ]
    }
  ]
}

Output ONLY valid JSON. Do not include markdown or commentary.
"""

PROMPTS = {
    "step1": STEP1_BASIC_INFO_PROMPT,
    "step2": STEP2_EXTERNAL_EVIDENCE_PROMPT,
    "step3": STEP3_FINAL_DECISION_PROMPT,
}
