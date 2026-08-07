# NPDPSS001000 — vizualna validacija diagrama

Datum pregleda: 2026-06-15
Artefakt: `NPDPSS001000-csd-dpp-udg-cmod.drawio`

## Izvedeni pregledi

| Pregled | Ukaz/metoda | Rezultat |
|---|---|---|
| Izvoz PNG/PDF | `drawio --version` in predvideni CLI izvoz | Ni izvedljiv: binarij `drawio` ni nameščen (`exit 127`). Tudi `draw.io`, `libreoffice`, `inkscape`, Chromium/Firefox in `wkhtmltoimage` niso na voljo. |
| XML/Draw.io struktura | `python3 drawio-skill/skills/drawio-skill/scripts/validate.py NPDPSS001000-csd-dpp-udg-cmod.drawio` | `0 error(s), 0 warning(s)` |
| Routing/overlap score | isti validator z `--score` | `0 through-vertex, 0 crossings, 0 overlaps` |
| Strani | Python XML parser | 6 strani, vse z naslovom in vsebino |
| Povezave | Python/XML validator | 36 robov, 0 manjkajočih endpointov, 0 robov brez geometrije |
| Identitete/containment | Python/XML validator | 112 unikatnih ID-jev, starši obstajajo |
| Label preflight | Python pregled vseh vertex celic | Vsi preverjeni elementi imajo veljavno geometrijo; dolga besedila so v ločenih širokih/visokih vozliščih ali lane opombah. |

## Rezultati po zahtevah

- **REQ-006:** PASS — strukturna validacija je uspešna; vizualnega odpiranja zaradi manjkajočega CLI ni bilo mogoče dokazati.
- **REQ-007:** PARTIAL — avtomatizirani routing/overlap pregled je uspešen, vendar PNG/PDF in dejanski vizualni pregled niso bili izvedeni.

## Omejitev

V tem workspace-u ni nameščenega draw.io desktop CLI niti drugega razpoložljivega rendererja. Zato ni mogoče objektivno potrditi dejanske rasterizirane berljivosti, odrezanih besedil, kontrasta ali puščic v izvozu. Diagram ni bil spreminjan, ker strukturni preflight ni pokazal napake, vizualnih popravkov pa brez renderja ni varno ugibati.

Za zaključni vizualni pregled je treba v okolju z draw.io CLI izvesti na primer:

```text
drawio -x -f png --page-index 1 --width 2000 -o NPDPSS001000-page-01.png NPDPSS001000-csd-dpp-udg-cmod.drawio
```

in ukaz ponoviti za strani 1–6; nato pregledati odrezana besedila, prekrivanja, kontrast in povezave.
