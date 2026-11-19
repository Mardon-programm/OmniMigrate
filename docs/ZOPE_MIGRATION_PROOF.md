# Zope full-repository migration proof

This is the result of running the complete Zope checkout through OmniMigrate's
LLM refactoring pipeline with deterministic anti-shrinkage contract enforcement.
The original checkout at `/home/mroot/Projects/test_zope/Zope` was not modified.

Artifacts (accepted files, rejected files, per-file diffs, JSONL report) live in
`/home/mroot/.cache/omni-zope/results/`. Reproduce with
`/home/mroot/.cache/omni-zope/run_zope_full_migration.py` (resumable, retries
errors) and aggregate with `/home/mroot/.cache/omni-zope/analyze.py`.

# Full Zope -> Python 3 migration report

Every Python file in the Zope checkout was sent through `LLMAgent.refactor_enforced()`: migration prompt, deterministic anti-shrinkage contract, up to 3 self-heal attempts. Original sources were never modified.

## Totals

| metric | value |
| --- | --- |
| unique files processed | 365 |
| accepted (`ok`) | 343 |
| rejected after retries | 0 |
| unresolved errors | 0 |
| skipped (empty/unreadable) | 22 |
| contract rejections caught before retry | 2 |
| accepted output files | 343 |
| accepted tree compiles | True |
| accepted files with changes | 343 |
| Python-2 / unparseable sources migrated | 1 |
| self-heal repairs | 14 |
| tokens (prompt / completion / total) | 771,460 / 580,868 / 1,352,328 |
| wall time, summed per file | 1095.7 min |
| median per-file time | 124.3 s |

## Models used for accepted files

| model | files |
| --- | --- |
| `gemini-3.5-flash-lite` | 184 |
| `gemini-3.1-flash-lite` | 159 |

## Preservation on accepted files

| metric | source | output | retained |
| --- | --- | --- | --- |
| top-level symbols | 1684 | 1691 | 100.4% |
| logic lines | 40424 | 39855 | 98.6% |

## Independent verification

| check | result |
| --- | --- |
| accepted outputs re-validated with current contract | 343 |
| outputs violating the contract after re-validation | 0 |
| `ruff check --select F821` (undefined names) | 0 errors |
| license headers deterministically restored | 20 |

## Contract violations (rejected + failed runs)

| code | count |
| --- | --- |
| `missing-symbols` | 2 |

## Largest accepted files

| file | symbols out/src | logic lines out/src | tokens |
| --- | --- | --- | --- |
| `src/ZPublisher/tests/testHTTPRequest.py` | 14/14 | 1273/1298 | 36,691 |
| `src/ZPublisher/tests/testHTTPResponse.py` | 3/3 | 1267/1281 | 34,206 |
| `src/ZPublisher/HTTPRequest.py` | 36/36 | 1238/1239 | 32,116 |
| `src/ZPublisher/HTTPResponse.py` | 30/30 | 690/893 | 32,054 |
| `src/OFS/Image.py` | 13/13 | 852/852 | 21,920 |
| `src/ZPublisher/tests/test_WSGIPublisher.py` | 13/13 | 800/808 | 21,404 |
| `src/OFS/interfaces.py` | 21/21 | 689/689 | 16,670 |
| `src/ZPublisher/tests/testBaseRequest.py` | 6/6 | 634/673 | 19,040 |
| `src/OFS/ObjectManager.py` | 14/14 | 622/622 | 16,124 |
| `src/ZPublisher/BaseRequest.py` | 12/12 | 505/608 | 13,742 |
| `src/OFS/tests/testObjectManager.py` | 10/10 | 530/530 | 14,727 |
| `src/webdav/Resource.py` | 2/2 | 495/495 | 14,233 |
| `src/OFS/tests/testTraverse.py` | 8/8 | 492/492 | 14,210 |
| `src/OFS/CopySupport.py` | 11/11 | 473/470 | 13,153 |
| `src/Products/PageTemplates/tests/testZopePageTemplate.py` | 25/25 | 444/444 | 13,415 |

## Notes on the enforcement design

* Each output is checked against a fingerprint of the original file (top-level
  symbols, logic-line count excluding imports, module docstring, imports, and
  newly introduced undefined names detected by pyflakes).
* A violation triggers up to three LLM self-heal attempts in
  `LLMAgent.refactor_enforced()`; only outputs that pass are accepted.
* Two real files were rejected during the run because the model renamed a
  top-level symbol (`ZRPPythonExprTest` and `somemethod`). Both were accepted
  after a retry, demonstrating that the guard is not merely declarative.
* Static analysis with `ruff --select F821` found one semantic regression
  (a dropped local alias `post_traverse`) that the original contract did not
  cover. An `undefined-names` guard was added to `code_contract.py`, the file
  was re-migrated, and all 343 accepted outputs now pass the strengthened
  contract with zero violations.
* Leading copyright/license comment blocks removed by the model were restored
  deterministically in 20 files; no executable code was changed by that step.
