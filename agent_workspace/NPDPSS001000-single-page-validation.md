# NPDPSS001000 — Validacija enostranskega master flowa

## Obseg
Izveden je bil namenski STEP-012 preflight za `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio`. Preverjena je vsebinska sledljivost do enostranskega layout plana in nativna XML struktura. To poročilo ne predstavlja vizualnega renderiranja.

## Strukturni rezultat

- Strani: **1** (zahtevano: 1)
- Celice: **195**
- Robovi: **104**
- Unikatni ID-ji: **True**
- Manjkajoči endpointi: **0**
- Robovi brez `mxGeometry`: **0**
- Ročni waypoint markup (`Array`, `<Array>`, `<mxPoint>`): **False**

## Sledljivostni rezultati

| Skupina | Zahtevano | Manjkajoče | Status |
|---|---:|---|---|
| `M-cards` | 34 | — | PASS |
| `controls` | 23 | — | PASS |
| `errors` | 4 | — | PASS |
| `manual` | 6 | — | PASS |
| `outputs` | 17 | — | PASS |
| `data` | 11 | — | PASS |
| `sql-procedure` | 7 | — | PASS |
| `edge-semantics` | 4 | — | PASS |
| `key-fields` | 10 | — | PASS |
| `roles` | 4 | — | PASS |
| `procedures` | 2 | — | PASS |
| `registrations` | 5 | — | PASS |
| `tables` | 10 | — | PASS |
| `integrations` | 6 | — | PASS |
| `outcomes` | 5 | — | PASS |

## Preverjeni viri in kriteriji

- Layout: `NPDPSS001000-single-page-layout-plan.md`.
- Vsebinski viri: `NPDPSS001000-source-inventory.md`, `NPDPSS001000-semantic-model.md`, `NPDPSS001000-outcome-decision-matrix.md`, `NPDPSS001000-technical-inventory.md`.
- Preverjeni so M01–M34, kontrole 2.a–7.g, X/R/D/S/A/P koridorji, T01–T11, Q01–Q04, procedure, registracije, ključna polja/statusi, sistemi in semantike robov.
- Rezultat je **PASS** za vsebinsko in strukturno sledljivost, če so vsi zgornji manjkajoči seznami prazni.

## Omejitev

Renderer ni bil uporabljen. Dejanska vizualna berljivost, kontrast, velikost pisave in odrezani napisi ostajajo predmet STEP-013; brez rendererja se ne označujejo kot uspešni.

## Layout korekcija po smernicah drawio-skill

Pregledani so bili `drawio-skill/skills/drawio-skill/references/xml-authoring.md`, `resources/file_resources/xml-reference.md` ter primeri `drawio-skill/assets/workflow.drawio` in `demo-layered.drawio`. Mapa `drawio-skill/asserts` v workspace-u ne obstaja; zato so bili uporabljeni razpoložljivi `assets/`, `references/` in `scripts/`.

Izključno enostranski diagram je bil minimalno korigiran:

- popravljena je bila napačna koordinata `M07`, ki je bila zunaj `lane_main`;
- L3 in L4 sta povečana, da so vsi `X/R/D/S` in `A/P` elementi znotraj svojih swimlane-ov;
- L4 in L5 sta prestavljena v ločena navpična koridorja;
- canvas je povečan na `6200 × 6700`, brez krčenja vsebine;
- swimlane kontejnerji imajo `pointerEvents=0`, otroške celice uporabljajo relativne koordinate;
- ohranjeni so glavni tok, ločeni exception/output koridorji, barvna semantika in legenda.

Objektivni containment preflight po spremembi: **0** elementov zunaj matičnega swimlane-a. Večstranski diagram ni bil spreminjan.

## Ponovljeni pregledi

- `upsert_drawio_diagram(action=validate)`: **PASS**; XML je veljaven po referenčnih pravilih.
- `validate.py`: **0 error(s), 0 warning(s)**.
- `validate.py --strict`: **0 error(s), 0 warning(s)**.
- `validate.py --score`: **score 0; 0 through-vertex, 0 crossings, 0 overlaps**.
- `git diff --check`: **PASS**.
- Renderer probe za `drawio`, `draw.io`, `libreoffice`, `soffice`, `inkscape`, Chromium/Chrome, Firefox in `wkhtmltoimage`: noben executable ni bil najden; PNG/PDF in rasterizirani pregled niso izvedeni.

Strukturni/layout preflight je uspešen, vendar vizualna berljivost še ni potrjena z renderjem.
