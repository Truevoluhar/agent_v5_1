# NPDPSS001000 — večstranski layout načrt draw.io diagrama

## Namen in načela

Ta dokument je izvedbeni načrt postavitve za `NPDPSS001000-csd-dpp-udg-cmod.drawio`; XML se v STEP-004 še ne izdeluje. Layout je izveden iz `NPDPSS001000-semantic-model.md`, `NPDPSS001000-outcome-decision-matrix.md` in `NPDPSS001000-source-inventory.md`. Ne uvaja novih poslovnih pravil. Nejasnosti ostanejo označene kot odprta vprašanja.

- **Smer glavnega toka:** levo → desno; paketna zanka je na spodnjem koridorju in se vrača na naslednjo PDF/vlogo.
- **Strani:** šest ločenih diagramov z enotnim naslovnim blokom, legendo in `Next/Prev` navigacijo.
- **Osnovni canvas:** 2200 × 1400 px; rob 40 px; naslov 70 px; legenda 150 px; delovni prostor 1100 px.
- **Berljivost:** največ 20–25 glavnih procesnih/odločitvenih vozlišč na strani; podatkovne opombe in tabele so sekundarne oblike, ne dodatna poslovna vozlišča.
- **Vrstni red:** `01` kontekst, `02` paket, `03` PDF kontrole, `04` izhodi, `05` podatki/SQL, `06` UDG/CMOD/poročanje.

## Skupna vizualna legenda

| Element | Oblika/barva | Uporaba |
|---|---|---|
| Proces | zaobljen pravokotnik, svetlo modra `#D6EAF8`, obroba `#2874A6` | izvajanje aplikacijske logike |
| Odločitev | diamant, svetlo rumena `#FCF3CF`, obroba `#B7950B` | samo eksplicitne kontrole/veje |
| Podatkovna tabela | valj, svetlo siva `#E5E7E9`, obroba `#566573` | EP/NP/DG/CMOD shramba |
| Vhod/izhodni dokument | dokumentna oblika, bela, obroba `#566573` | XLSX, ZIP, PDF, e-pošta |
| Integracijski klic | pravokotnik, oranžna `#FAD7A0`, obroba `#CA6F1E` | procedure, web service, queue |
| Uspeh/hramba | zaobljen pravokotnik, zelena `#D5F5E3`, obroba `#239B56` | `SF_REZULTAT=1`, AVT/PIZ hramba |
| Napaka/ročna obravnava | zaobljen pravokotnik, rdeča `#F5B7B1`, obroba `#C0392B` | `SF_REZULTAT=2`, SD ali tehnična napaka |
| Pravica/varnost | vijolična `#E8DAEF`, obroba `#7D3C98` | `DPP_PDF_BJ` |
| Odprto vprašanje | oranžno-rumena opomba `#FEF5E7`, črtkana obroba | tip 4, `TP_OPOMBA`, faze, prejemnik e-pošte |
| Rob | polna temno modra puščica | normalni tok |
| Izjemni rob | rdeča puščica, po možnosti črtkana | napaka/ročna veja |
| Podatkovni rob | oranžna puščica | branje, zapis ali klic; oznaka `read/write/call/message` |

Vsaka stran ima majhno legendo v zgornjem desnem kotu; celotna legenda je na strani 01.

## ID-shema in containment

- Strani: `pg_context`, `pg_batch`, `pg_pdf`, `pg_outcomes`, `pg_tech`, `pg_docflow`.
- Koren strani: `0` in `1`; naslov/legenda sta neposredna otroka `1`.
- Swimlane kontejnerji: `lane_<page>_<role>`; vse pripadajoče procesne celice imajo `parent` na lane.
- Procesi: `p_<page>_<nn>`; odločitve: `d_<page>_<nn>`; podatki: `t_<page>_<nn>`; integracije: `i_<page>_<nn>`; terminali: `e_<page>_<nn>`; opombe: `n_<page>_<nn>`.
- Robovi: `edge_<page>_<nn>`; čez strani ni robov med draw.io zavihki. Namesto tega so na robu strani jasno označeni `NEXT: pg_x` / `PREV: pg_x`.
- Navigacijski gumbi so otroci naslovnega kontejnerja, niso del poslovnega toka.
- Vsa ozadja so starši (swimlane/container), ne ročno prekrivanje; vozlišče je v enem in samo enem vsebinskem lane-u.
- Edini cross-lane robovi so dovoljeni, kadar tok prehaja med akterji/sistemi; rob naj bo ortogonalen in brez waypoint arrayev.

## Stran 01 — Sistemski kontekst in sledljivost

**Namen:** en pogled na sisteme, vhod/izhod in odgovornosti; brez podrobnih poslovnih odločitev.

**Swimlane-i (vodoravno, višina približno 250 px):**
1. Operativa/uporabnik
2. BiZPIZ + EP
3. NPDPSS001000
4. UDG/DG/eDosje
5. CMOD
6. Obvestila/e-pošta

**Pozicije (x,y,w,h):**
- Operativa: `(40,180,2100,160)`; BiZPIZ/EP `(40,340,2100,180)`; NP `(40,520,2100,220)`; DG `(40,740,2100,180)`; CMOD `(40,920,2100,160)`; obvestila `(40,1080,2100,150)`.

**Glavne oblike:**
- `t_context_01`: `EP.VLOGE_ODDANE`, `EP.PRIPONKE_ODDANE` v BiZPIZ/EP (x=120).
- `p_context_01`: prejem eVloge 014-47-1 + ZIP (x=410).
- `p_context_02`: NPDPSS001000 paketni proces (x=760).
- `t_context_02`: `NP.CSD_DPP_PDF` in `NP.CSD_DPP_OBDELAVA` (x=1050).
- `i_context_01`: `DG.P_POISCI_ZADEVO` / `DG.P_ZAKLJUCI_ZADEVO` (x=1400).
- `t_context_03`: `DG.OSEBA`, `DG.IDENTIFIKATOR`, `DG.ZADEVA`, `DG.DOKUMENT`, `DG.POT_ZADEVE` (x=1660).
- `i_context_02`: CMOD queue `Q.SF.CM.LOAD.PDF.SIGN.IN` in CMOD lane (x=1430,y=970).
- `i_context_03`: `NPPZSS001000.insertPzIzbor` in CMOD/UDG tok (x=1720,y=970).
- `p_context_03`: poročilo po e-pošti (x=1840,y=1120).

**Robovi:** vhod → NP je modri tok; NP → DG so oranžni `read/write/call`; DG → CMOD je oranžni `message`; NP → e-pošta je modri tok. Legenda in odprta vprašanja (tip 4, e-poštni prejemnik) na desni spodaj.

## Stran 02 — Glavni paketni izvajalni tok

**Namen:** od pravice do paketne zanke in poročila; PDF podrobnosti so sklicane na stran 03.

**Swimlane-i (vodoravno):** Operativa, BiZPIZ/EP, NPDPSS001000, UDG/DG, Poročanje.

**Glavni koridor:** y=430, x od 80 do 2050; napake zgoraj y=220; iteracijska zanka spodaj y=950.

**Zaporedje glavnega toka:**
1. `p_batch_01` zagon (80,430) → `d_batch_01` pravica `DPP_PDF_BJ` (250,430).
2. NE → `e_batch_01` »uporabnik nima pravice« (250,220); DA → `d_batch_02` nova vloga/priloga, join `EP.VLOGE_ODDANE + EP.PRIPONKE_ODDANE`, `SY_TISP <> 'B'` (520,430).
3. NE → `e_batch_02` »ni nove priloge« (520,220); DA → `p_batch_02` izberi eVlogo/ZIP (790,430).
4. `p_batch_03` evidentiraj `014-47-1`, CSDLJ, klasifikacijo `10390`, `DT_PREJEMA` (1040,430).
5. `i_batch_01` `DG.P_POISCI_ZADEVO(...,'014-47-1',...,GUID)` → `t_batch_01` `ID_ZADEVA`; nato `p_batch_04` nastavi `DG.ZADEVA.DT_ZACETEK=DT_PREJEMA` (1320–1650,430).
6. `p_batch_05` razpakiraj ZIP; ne-PDF ignoriraj (1750,430) → `d_batch_03` še PDF? (1950,430).
7. DA navzdol do `p_batch_06` »obdelaj eno PDF« (1950,700), s klicem na `pg_pdf`; NE na `p_batch_07` »zaključi paket« (1950,520).
8. `p_batch_07` → `p_batch_08` sestavi e-poštno poročilo → `p_batch_09` Excel rezultat → `d_batch_04` naslednja vloga/ZIP?; DA se vrne na `p_batch_02`, NE → `e_batch_03` konec (1800–2100,950–1150).

**Opombe:** `SF_REZULTAT NULL/1/2` v legendi; izhod posamezne PDF vedno vrne na `d_batch_03`; celoten procesni konec je šele po poročilu.

## Stran 03 — Podrobna kontrola ene PDF odločbe

**Namen:** vse kontrole 1–6, brez razširjanja končnih vej 7.a–7.g.

**Swimlane-i:** PDF/parser; NPDPSS001000; DG/identiteta; status/zapis.

**Koridorji:** glavni tok y=470; napake y=180; nadaljevanje v izhode y=900; 3×3 grid za odločitve, da se robovi ne križajo.

**Zaporedje in pozicije:**
- `p_pdf_01` berljivost PDF (80,470) → `p_pdf_02` ustvari/posodobi `NP.CSD_DPP_PDF` (300,470).
- `p_pdf_03` preberi 13-mestni EMŠO → `d_pdf_01` EMŠO prebran? (540,470); NE → `e_pdf_01` `SF_REZULTAT=2`, »EMŠO ni bil prebran« (540,180).
- DA → `d_pdf_02` EMŠO = ime datoteke? (780,470); NE → `p_pdf_04` zapiši »EMŠO ni enak«, nato še vedno iskanje osebe (780,250); DA neposredno naprej.
- `i_pdf_01` poišči po `DG.IDENTIFIKATOR` (`ID_TIP_IDENT IN (1,9)`, aktivni, 13 znakov) (1020,470) → `d_pdf_03` rezultat 0/>1/1 (1260,470).
- 0 → `e_pdf_02` neznana oseba; >1 → `e_pdf_03` neurejeni identifikatorji; 1 → `p_pdf_05` shrani `SF_OSEBE` (obe napaki na y=180, normalni tok y=470).
- `d_pdf_04` ali je bil EMŠO neusklajen? → ne `p_pdf_06` prepoznaj tip; da označi SD kandidat (1440,700), nato tip.
- `p_pdf_06` shrani `SF_ODLOCBA_BRANA`; `d_pdf_05` tip prepoznan? (1660,470); NE → `e_pdf_04` tip neznan; DA → `d_pdf_06` vhodni/prebrani tip enak? (1880,470); NE → `e_pdf_05` tip ni enak; DA → `p_pdf_07` preveri `NP.CSD_DPP_OBDELAVA`.
- `d_pdf_07` EMŠO v predhodnih obdelavah? → NE `e_pdf_06` »Ni v predhodnjih obdelavah CSD«; DA → `p_pdf_08` preberi `TP_OPOMBA`, `DD_SKLEP_ODLOCBA`, `SF_REZULTAT`.
- `d_pdf_08` obstaja uspešna odločba drugega tipa? → DA `e_pdf_07` dvojnik; NE → `d_pdf_09` matrika 7.a–7.g; vsi izhodi imajo navigacijo na stran 04.

**Statusni trak:** pod lane-om `NP.CSD_DPP_PDF`: `SF_REZULTAT=NULL` pred obdelavo; `2` ob napaki; `1` ob uspehu; `DT_OBDELAVA` vedno ob zaključku. Opomba: znana oseba lahko gre na `DT_SMRT` kontrolo tudi pri napaki; neznana oseba ne.

## Stran 04 — Odločitvena matrika in terminalni izhodi

**Namen:** pregledno prikazati 7.a–7.g ter razliko med AVT, PIZ, SD in mrtvim primerom.

**Swimlane-i:** NP odločanje, DG/UDG zadeva, strokovni delavec/PIZ, status.

**Postavitev:** `d_out_01` matrika v sredini (x=860,y=430,w=280,h=160); sedem vej v dveh vrstah, da ni križanj.

- 7.a, 7.b, 7.c v zgornji vrstici (x=80,360,640; y=230) → skupni `p_out_01` AVT hramba (x=940,y=230).
- 7.e, 7.f v zgornji vrstici (x=1240,1600; y=230) → isti AVT proces.
- 7.d spodaj (x=80,y=760) → `p_out_02` PIZ bazen (x=430,y=760).
- 7.g/vse drugo spodaj (x=800,y=760) → `d_out_02` `DG.OSEBA.DT_SMRT`? (x=1160,y=760).
- `d_out_02` DA → `e_out_01` mrtva oseba: brez SD, avtomatsko zapiranje (x=1500,y=650); NE → `p_out_03` ustvari/dodeli `014-47-1-SD` po razdelilniku (x=1500,y=900).

**AVT podtok (v zelenem kontejnerju):** `p_out_01` ustvari `014-47-1-AVT` → `t_out_01` `DG.DOKUMENT` (`ID_VRSTA_DOK=1341`, `ID_FORMAT=3`, `ID_STATUS=2`) → `t_out_02` `DG.POT_ZADEVE` brez PVI → `i_out_01` `DG.P_ZAKLJUCI_ZADEVO(ID_ZADEVA,3,15248,10,4676,NULL,NULL,NULL)` → `e_out_02` `SF_REZULTAT=1`.

**PIZ podtok:** `p_out_02` `DO-PONOVNO IZPLAČILO PO MIROVANJU`, vloga `014-47-1-PIZ`, `ID_SIGN_ZNAK` po registraciji, nato rezultat 1 in `ID_ZADEVA`.

**SD podtok:** `p_out_03` `DG.P_POISCI_ZADEVO(...,'014-47-1-SD',...)` → popravek `DT_ZACETEK=DT_PREJEMA` → dodelitev po razdelilniku → rezultat/opomba in `DT_OBDELAVA`. Rdeča napaka brez `SF_OSEBE` se konča brez SD in brez AVT zaključka.

**Matrika kot opomba:** 7.a `1/08`; 7.b `2/(03,08)`; 7.c `3/08`; 7.d `4` (odprto pravilo); 7.e `5/07`; 7.f `6/07`; 7.g vse drugo.

## Stran 05 — Podatkovni model, SQL kontrole in procedure

**Namen:** tehnična sledljivost brez obremenitve poslovnega toka; povezave so označene z `read`, `write`, `call`.

**Swimlane-i:** EP podatki; NP podatki; DG/UDG podatki; procedure/SQL.

**Razporeditev:** tri stolpce shramb in spodnji trak tehničnih klicev.

- EP stolpec (x=100): `t_tech_01` `EP.VLOGE_ODDANE`; `t_tech_02` `EP.PRIPONKE_ODDANE`.
- NP stolpec (x=720): `t_tech_03` `NP.CSD_DPP_PDF` z jedrnimi polji; `t_tech_04` `NP.CSD_DPP_OBDELAVA` z `TP_OPOMBA`, `DD_SKLEP_ODLOCBA`, `SF_REZULTAT`.
- DG stolpec (x=1340): `t_tech_05` `DG.OSEBA`; `t_tech_06` `DG.IDENTIFIKATOR`; `t_tech_07` `DG.ZADEVA`; `t_tech_08` `DG.DOKUMENT`; `t_tech_09` `DG.POT_ZADEVE`.
- Spodnji integracijski trak: `i_tech_01` `DG.P_POISCI_ZADEVO` (osnovna zadeva `014-47-1`, SD, AVT); `i_tech_02` `DG.P_ZAKLJUCI_ZADEVO` s parametri; `i_tech_03` update `DG.ZADEVA.DT_ZACETEK`; `i_tech_04` `SS.EVIDENTIRANJE_VLOG` (registracije `014-47-1-PIZ/AVT/SD`).

**SQL/opombe na desnem robu:**
- EP/NP join: nova vloga/priloga in `SY_TISP <> 'B'`.
- identifikator: `ID_TIP_IDENT IN (1,9)`, `LENGTH=13`, `SF_IDENT=SF_EMSO`, `SF_AKTIVEN_IDENT='D'`.
- predhodne obdelave: isti EMŠO in `SY_TISP <> 'B'`.
- dvojnik: isti `SF_OSEBE`, drug `SF_ODLOCBA_BRANA`, `SF_REZULTAT <> 2`.
- `DG.POT_ZADEVE`: brez PVI; ne dopolni manjkajoče faze, ampak dodaj opombo »vir navaja faze 2/5/6/25 — preveriti mapiranje«.

## Stran 06 — UDG/CMOD dokumentni tok in poročanje

**Namen:** podrobno prikazati, kaj se zgodi po odločitvi pri dokumentu, poti zadeve, PIZ/CMOD in paketnem poročilu.

**Swimlane-i (navpični, sistemi kot stolpci):** NPDPSS001000 | UDG/eDosje | CMOD | PIZ integracija | E-pošta.

**Glavni koridor:** y=520, sistemi od leve proti desni; status/povratne informacije po spodnjem koridorju y=950.

**Glavne oblike:**
- `p_doc_01` izhod strani 04: AVT/PIZ/SD izhod (x=100).
- `i_doc_01` UDG registracija/evidentiranje in `t_doc_01` `DG.DOKUMENT` (x=420–760).
- `t_doc_02` `DG.POT_ZADEVE`, z opombo brez PVI (x=820).
- `i_doc_02` CMOD queue `Q.SF.CM.LOAD.PDF.SIGN.IN` (x=1040) → `p_doc_02` masovni zajem/CMOD (x=1260).
- `i_doc_03` `NPPZSS001000.insertPzIzbor` (x=1480) in `i_doc_04` `ZPIZCPR/setObvestiloWS` (x=1690), oba v PIZ integracijskem lane-u.
- `p_doc_03` sestavi rezultate in `p_doc_04` pošlji e-pošto z nazivom ZIP, datumom prejema, vhodnim tipom, tabelo rezultatov in številom primerov (x=1750–2050,y=700).

**Robovi:** dokument → UDG `write`; UDG → CMOD `message`; PIZ → servisi `call`; paketni rezultat → e-pošta `message`. Vsak klic je oranžen; statusi `SF_REZULTAT`, `TX_OPOMBA`, `DT_OBDELAVA`, `ID_ZADEVA` so vijolično označeni na spodnjem traku.

**Odprta vprašanja v rumenih opombah:** prejemnik e-pošte ni določen; natančne faze `DG.POT_ZADEVE` niso popolnoma preslikane; tip odločbe 4 preveriti v specifikaciji; celoten `TP_OPOMBA` šifrant ni podan.

## Medstranska sledljivost

| Izvorni odsek | Stran | Vozlišča/artefakt |
|---|---|---|
| pravica in nova vloga | 02 | `B01–B10`, `d_batch_01/02` |
| ZIP/PDF iteracija | 02–03 | `B10–B16`, `P01–P03` |
| EMŠO/oseba | 03 | `P04–P17` |
| tip odločbe/CSD/dvojnik | 03 | `P18–P30` |
| izhodi 7.a–7.g, DT_SMRT | 04 | `P30–P33`, `O01–O10` |
| tabele/statusi/procedure | 05 | `NP.*`, `DG.*`, SQL opombe |
| dokument/pot/CMOD/PIZ/e-pošta | 01, 04, 06 | kontekst + `O05–O10` + dokumentni tok |

## Validacijski kriteriji layouta

1. Šest strani ima pravilna imena in vrstni red.
2. Vsaka stran ima naslov, namen, lokalno legendo in navigacijo.
3. Vsak glavni tok ima jasno začetno in končno točko; izjemni koridorji niso pomešani z glavnim tokom.
4. Vse zahteve REQ-001–REQ-007 so sledljive na vsaj eno stran; REQ-006/007 sta za XML fazi, zato tu ostajata `PENDING`.
5. Nobeno poslovno vozlišče ni anonimno; uporablja semantični ID ali tehnično ime.
6. Vse povezave so ortogonalne in bodo v XML izvedene kot `mxCell edge=1` z osnovno geometrijo brez ročnih waypointov.
7. Vsebina ne vsebuje trditev zunaj vira; odprta vprašanja so vidno označena.
8. Pred izdelavo XML se izvede še pregled `drawio-skill` pravil v STEP-006.
