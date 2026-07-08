# Cleanup Manifest

Cleanup date: 2026-07-07

## Policy

Questionable legacy material was quarantined, not deleted. Only generated junk was removed.

## Quarantined

- `paper/dapps2026` -> `koan-submission/archive/legacy_dapps2026/`
- `IEEE-conference-template-062824` -> `koan-submission/archive/legacy_templates/`
- `conference-latex-template.zip` -> `koan-submission/archive/legacy_templates/`
- `Report_Template_for_Major_Project_for_B_Tech__SRM_Institute_of_Science_and_Technology` -> `koan-submission/archive/legacy_templates/`
- `Report_Template_for_Major_Project_for_B_Tech__SRM_Institute_of_Science_and_Technology.zip` -> `koan-submission/archive/legacy_templates/`
- Review/admin files and old deliverables -> `koan-submission/archive/legacy_review_docs/`
- `lossfunk_doing_science_that_matters.html` -> `koan-submission/archive/legacy_review_docs/`

## Deleted generated junk

- `.DS_Store` files.
- LaTeX auxiliary/build files: `.aux`, `.log`, `.out`, `.fls`, `.fdb_latexmk`, `.synctex.gz`, `.blg`.
- Temporary PDF text/image renders under `tmp/pdfs/`.
- Stray `excalidraw.log` files.
- Stray `Icon<CR>` file.
- Empty `paper/` and `tmp/` directories after cleanup.

## Not removed yet

- `backend/dist/`: tracked generated build output; review later.
- `backend/hack.txt`: tracked questionable file; review later.
- `scripts/`: retained because scripts may be useful for benchmark adapters and verification.
- `agents/`, `backend/src/`, `frontend/`, `contracts/`: retained as source.
