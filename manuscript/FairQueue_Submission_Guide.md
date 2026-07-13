# FairQueue — F1000Research submission guide and checklist

*Article type:* **Software Tool Article** · *Platform:* F1000Research (post-publication peer review) · *ISSN 2046-1402*

This guide lists everything F1000Research requires for a Software Tool Article, what is already prepared, and the few items only you can complete before uploading.

## 1. Files to upload

| Item | Status | Notes |
|---|---|---|
| Manuscript (.docx) | Ready | `FairQueue_Manuscript_F1000.docx` — title, structured abstract, keywords, Introduction, Methods (Implementation + Operation), Results, Use Cases, Discussion/Conclusions, availability, declarations, references, figure legends. |
| Figures (separate files) | Ready | `figures/Figure1–5*.png` (RGB, line art). Uploaded as individual files; legends are at the end of the manuscript. |
| Cover letter | Ready | `FairQueue_CoverLetter.docx` — add your name, affiliation, date. |
| Source code (GitHub) | To do | Push the project to a public repository (see §4). |
| Archived code (Zenodo) | To do | Link GitHub to Zenodo and mint a DOI (see §4). |
| Extended data (Zenodo) | To do | Archive `data/processed/*`, `outputs/`, `data_catalogue.csv`; get a DOI. |
| LICENSE | Ready | `LICENSE` (MIT) in the repository root. |

## 2. Author-specific items to complete (required)

- **Author name(s), affiliation(s) and order** — replace the `[Surname]`/`[Department, Institution…]` placeholders in the manuscript and cover letter.
- **ORCID iD for the submitting author** — mandatory; register free at orcid.org if needed.
- **Email and corresponding-author details.**
- **CRediT contributions** — entered in the submission system (template in §3).
- **Competing interests** — the manuscript states "No competing interests were disclosed"; change if not true.
- **Grant information** — currently "no grants"; change if funded.
- **GitHub URL, Zenodo software DOI, Zenodo extended-data DOI** — insert into the manuscript's Data and Software Availability section once created.
- **At least five reviewer suggestions** — see §5.

## 3. CRediT author contributions (template)

| Role | Author |
|---|---|
| Conceptualization | [Author] |
| Methodology | [Author] |
| Software | [Author] |
| Formal Analysis | [Author] |
| Data Curation | [Author] |
| Visualization | [Author] |
| Writing – Original Draft | [Author] |
| Writing – Review & Editing | [Author] |

## 4. Publishing the code and data (open-source requirements)

F1000Research requires software in an open language (Python — met), source code on a version-control system, and an archived copy with a DOI under an OSI-approved licence.

**GitHub (source code):**
1. Create a public repository, e.g. `fairqueue-simulator`.
2. From the project folder: `git init`, `git add .`, `git commit -m "FairQueue Simulator v1.0"`, then push. The included `.gitignore` keeps the large raw data and `Data.zip` out of the repo; the processed datasets and code are retained.
3. Add a release tag, e.g. `v1.0.0`.

**Zenodo (archived code + DOI):**
1. Sign in to zenodo.org with GitHub and enable the repository under Settings → GitHub.
2. Publish the `v1.0.0` release on GitHub; Zenodo automatically archives it and issues a DOI.
3. Copy the version DOI into the manuscript's "Archived source code at time of publication" line.

**Zenodo (extended data + DOI):** create a separate Zenodo upload containing `data/processed/`, `outputs/` and `data_catalogue.csv`; choose CC-BY 4.0; copy the DOI into the "Extended data" statement.

## 5. Reviewer suggestions (need at least five)

F1000Research is author-led: you must suggest ≥5 reviewers who are qualified, have relevant expertise, hold a PhD or equivalent standing, and have no conflict of interest (not recent co-authors, not from your institution). Suitable expertise areas for this article: NHS elective-care / waiting-list analytics; health-services research and health inequalities; operational research in healthcare; machine learning / explainable AI in health; open health data science. For each suggestion record: full name, institutional email, affiliation, and a one-line justification.

| # | Name | Affiliation | Email | Expertise / justification |
|---|---|---|---|---|
| 1 | [ ] | [ ] | [ ] | [ ] |
| 2 | [ ] | [ ] | [ ] | [ ] |
| 3 | [ ] | [ ] | [ ] | [ ] |
| 4 | [ ] | [ ] | [ ] | [ ] |
| 5 | [ ] | [ ] | [ ] | [ ] |

## 6. Before you click submit

- Language consistent (UK or US English) throughout.
- Abstract ≤300 words, structured Background/Methods/Results/Conclusions, no citations. (Current draft complies.)
- Up to 8 keywords. (Provided.)
- All figures/tables cited in the text; legends at the end; figure titles ≤15 words.
- Data Availability Statement present (mandatory) with repository DOIs filled in.
- Software availability: GitHub URL, Zenodo DOI, MIT licence stated.
- ORCID for submitting author ready.
- Article Processing Charge: F1000Research levies an APC on acceptance for peer review — check current rate and any waiver/fee-support you may be eligible for before submitting.
