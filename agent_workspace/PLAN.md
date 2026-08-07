# Execution Plan

## Metadata
- **Plan ID:** NPDPSS001000-DRAWIO
- **Last updated:** 2026-06-15
- **Owner:** PLANNER agent
- **Status:** ACTIVE — EXTENDED SCOPE
- **Source:** `NPDP - Navodila za programiranje - Shranjevanje CSD DPP v UDG NPDPSS001000.doc`
- **Primary output:** `NPDPSS001000-csd-dpp-udg-cmod.drawio`
- **Additional output:** `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio`

## Objective
Ustvariti zelo podroben, tehnično pravilen in vizualno berljiv draw.io diagram, ki na podlagi navodil NPDPSS001000 natančno prikaže celoten postopek od prejema eVloge 014-47-1 in ZIP priloge iz BiZPIZ do preverjanja, obdelave PDF odločb, evidentiranja v UDG/CMOD, avtomatskega zaključevanja ali dodelitve strokovnemu delavcu ter poročanja po e-pošti. Poleg obstoječega večstranskega diagrama izdelati še enostranski »master flow«, kjer so celoten proces, vse odločitve, podatki, tehnični klici, izhodi in poročanje na enem platnu.

## Scope
- Razčlenitev izvornega `.doc` dokumenta in izločitev dejanskih poslovnih korakov, odločitev, tabel, procedur, SQL kontrol, vlog in integracij.
- Izdelava večstranskega draw.io dokumenta, ker izvor vsebuje pregledni proces in podrobnosti implementacije.
- Izdelava dodatnega enostranskega draw.io dokumenta z enim platnom in celotnim end-to-end tokom; ta dokument je namenoma zelo širok/visok in uporablja več nivojev zgoščevanja, da ohrani vse podatke brez razdelitve na strani.
- Priporočena struktura strani:
  1. **Pregled procesa / sistemski kontekst** — BiZPIZ, EP tabele, NPDPSS001000, UDG/eDosje, CMOD, e-pošta.
  2. **Glavni izvajalni tok** — pravice, nova vloga, izdelava zadeve, ZIP/PDF obdelava, zaključek paketa.
  3. **Podrobna kontrola posamezne PDF odločbe** — EMŠO, SF_OSEBE, tip odločbe, zgodovina CSD in deduplikacija.
  4. **Odločitvena matrika in izhodi** — avtomatska hramba, bazen PIZ, strokovni delavec, napake.
  5. **Podatkovni model in tehnični klici** — `NP.CSD_DPP_PDF`, `NP.CSD_DPP_OBDELAVA`, `DG.P_POISCI_ZADEVO`, `DG.P_ZAKLJUCI_ZADEVO`, `DG.DOKUMENT`, `DG.POT_ZADEVE`, CMOD queue in servisi.
  6. **Konfiguracija, UDG/CMOD dokumentni tok in poročanje** — registracije vlog, dokument, pot zadeve, masovni zajem CMOD, email.
- Uporaba slovenskih oznak iz dokumenta, pri tehničnih imenih ohranitev originalnih imen tabel, polj, procedur in kod.
- Vizualno ločevanje uspešnih poti, napak, ročne obravnave in avtomatskega zaključka.

## Out of Scope
- Implementacija aplikacije, SQL procedur, uporabniškega vmesnika ali CMOD/UDG integracije.
- Spreminjanje vsebine izvornih programskih navodil.
- Dodajanje tehnologij, poslovnih pravil ali povezav, ki niso navedene ali jasno razvidne iz dokumenta.
- Produkcijsko izvajanje klicev v BiZPIZ, UDG, Oracle ali CMOD.

## Current State
- Izvorni 18-stranski `.doc` dokument je identificiran in vsebinsko normaliziran v `NPDPSS001000-source-inventory.md`.
- Semantični model (`NPDPSS001000-semantic-model.md`) in matrika končnih izhodov (`NPDPSS001000-outcome-decision-matrix.md`) obstajata, sta ne-prazna in sta bila validirana z izhodno kodo 0.
- Predpogoji za STEP-004 so izpolnjeni: STEP-002 in STEP-003 sta `DONE`/`PASSED`; ni aktivnega blockerja.
- Ciljni `NPDPSS001000-csd-dpp-udg-cmod.drawio` in `.bak` trenutno ne obstajata v workspace root-u; git status kaže njuno predhodno brisanje, zato ju ni dovoljeno obravnavati kot veljavna izhoda.
- STEP-004 je izveden in validiran: konkreten šeststranski layout načrt je v `NPDPSS001000-layout-plan.md`; XML diagrama se v tem koraku še ne izdeluje.
- STEP-005 je izveden in validiran: tehnični inventar podatkov, SQL kontrol, procedur, registracij, dokumentnega toka, CMOD/PIZ klicev in poročanja je v `NPDPSS001000-technical-inventory.md`.
- `drawio-skill` repozitorij je prisoten; avtorska pravila iz `resources/file_resources/xml-reference.md` in `drawio-skill/skills/drawio-skill/references/xml-authoring.md` so bila prebrana za STEP-006.
- STEP-006 je izveden: ciljni šeststranski XML obstaja in je strukturno validiran; STEP-007 je naslednji korak za izvoz in vizualni pregled.

## Assumptions
- Primarni uporabnik diagrama je razvijalec/integrator, sekundarni pa tester in poslovni skrbnik.
- Diagram bo imel več strani, glavni tok bo levo-desno, časovni/izvedbeni podtok pa bo prikazan zaporedno z jasno označenimi swimlane-i.
- `SF_REZULTAT`: prazno = neobdelano, `1` = uspešno obdelano, `2` = obdelano z napako; te kode se prikažejo kot eksplicitna legenda.
- Pri nejasnih ali poškodovanih delih `.doc` bo diagram označil **predpostavko/odprto vprašanje**, ne pa izmišljal podrobnosti.
- Ločene strani so bolj primerne kot preobremenitev ene strani; vsaka stran mora biti samostojno razumljiva z naslovom in legendo.
- Nova enostranska različica je zahtevana kljub večji gostoti; berljivost se bo zagotavljala z velikim canvasom, jasnimi horizontalnimi pasovi, minimiziranimi križanji, lokalnimi legendami in sledljivimi ID-ji.

## Requirements

### REQ-001 — Vsebinski izvor
- **Priority:** MUST
- **Description:** Diagram mora temeljiti na navodilih NPDPSS001000.
- **Acceptance:** V diagramu so sledljivi koraki prejema, obdelave, evidentiranja, zaključevanja in poročanja iz dokumenta.
- **Status:** PENDING
- **Linked steps:** STEP-001, STEP-002, STEP-003

### REQ-002 — Celotni procesni tok
- **Priority:** MUST
- **Description:** Prikazan mora biti tok od preverjanja pravice `DPP_PDF_BJ` do naslednje vloge/datoteke in končnega poročila.
- **Acceptance:** Prikazane so vse glavne veje za nedovoljeno pravico, neobstoječo novo vlogo, ZIP/PDF obdelavo, napake in končne izhode.
- **Status:** PENDING
- **Linked steps:** STEP-002, STEP-003, STEP-004

### REQ-003 — Poslovne odločitve in napake
- **Priority:** MUST
- **Description:** Prikazane morajo biti kontrole EMŠO, osebe, tipa odločbe, predhodnih CSD podatkov, podvojitev, smrti in kombinacij `DD_SKLEP_ODLOCBA`/`TP_OPOMBA`.
- **Acceptance:** Vsaka odločitev ima jasno vejo Da/Ne oziroma konkretne izhode ter navedene kode/opombe napak.
- **Status:** PENDING
- **Linked steps:** STEP-002, STEP-003, STEP-004

### REQ-004 — Sistemi, tabele in integracije
- **Priority:** MUST
- **Description:** Diagram mora prikazati BiZPIZ, EP, NP, DG/UDG/eDosje, CMOD, CMOD queue in e-pošto ter smeri podatkov.
- **Acceptance:** Prikazane so vsaj tabele `EP.VLOGE_ODDANE`, `EP.PRIPONKE_ODDANE`, `NP.CSD_DPP_PDF`, `NP.CSD_DPP_OBDELAVA`, `DG.OSEBA`, `DG.IDENTIFIKATOR`, `DG.ZADEVA` in dokument/pot zadeve.
- **Status:** PENDING
- **Linked steps:** STEP-001, STEP-005

### REQ-005 — Tehnična sledljivost
- **Priority:** MUST
- **Description:** Ključni klici in SQL kontrole morajo biti vidni v tehnični strani ali opombah.
- **Acceptance:** Vključeni so `DG.P_POISCI_ZADEVO`, `DG.P_ZAKLJUCI_ZADEVO`, update `DT_ZACETEK`, dokument `ID_VRSTA_DOK=1341`, CMOD queue in navedeni web-service klici.
- **Status:** PENDING
- **Linked steps:** STEP-005

### REQ-006 — Uredljiv in veljaven draw.io XML
- **Priority:** MUST
- **Description:** Izhod mora biti nativni, uredljiv `.drawio` XML brez dangling povezav ali neveljavne geometrije.
- **Acceptance:** `validate.py` uspe; ID-ji so unikatni, starši obstajajo, robovi imajo geometrijo, HTML oznake so pravilne, diagram se odpre v draw.io.
- **Status:** PENDING
- **Linked steps:** STEP-006, STEP-007

### REQ-007 — Berljivost in vizualni pregled
- **Priority:** MUST
- **Description:** Diagram mora biti zelo podroben, vendar pregledno razporejen z barvno semantiko, legendami, swimlane-i, ortogonalnimi povezavami in brez prekrivanj.
- **Acceptance:** PNG/PDF izvoz je berljiv pri običajnem zoomu; ni odrezanih besedil, prekrivanj, nejasnih puščic ali križanj glavnega toka.
- **Status:** PENDING
- **Linked steps:** STEP-006, STEP-007

### REQ-008 — Enostranski celotni master flow
- **Priority:** MUST
- **Description:** Izdelan mora biti dodaten nativni draw.io diagram z eno samo stranjo, ki vsebuje celoten end-to-end flow NPDPSS001000.
- **Acceptance:** Ena stran prikazuje vhod, pravico, novo vlogo, paketno zanko, vse kontrole 2.a–6.b, odločitve 7.a–7.g, podatke/tabele, procedure, UDG/CMOD/PIZ integracije, izhode in e-poštno poročanje.
- **Status:** IN_PROGRESS — XML, structural and dedicated traceability validation passed; visual validation pending
- **Linked steps:** STEP-010, STEP-011, STEP-012, STEP-013

### REQ-009 — Popolna podatkovna in tehnična sledljivost na eni strani
- **Priority:** MUST
- **Description:** Enostranski diagram mora ob poslovnem toku prikazati tudi vse zahtevane podatkovne objekte, ključna polja/statusne vrednosti, SQL kontrole, procedure, konfiguracijo in robne semantike.
- **Acceptance:** Vsak ključni objekt/klic iz `NPDPSS001000-technical-inventory.md` je v diagramu ali povezani opombi, vsak tehnični rob ima oznako `read`, `write/update`, `call` ali `message`, odprta vprašanja pa so jasno označena.
- **Status:** PASSED — XML content and dedicated traceability report passed; visual rendering not required for data traceability
- **Linked steps:** STEP-010, STEP-011, STEP-012

### REQ-010 — Enostranska berljivost in nativna uredljivost
- **Priority:** MUST
- **Description:** Enostranski master flow mora biti nativno uredljiv, strukturno veljaven in vizualno pregledljiv kljub veliki gostoti informacij.
- **Acceptance:** Datoteka ima točno eno diagram stran, unikatne ID-je, veljavne starše/geometrijo/robove, brez waypoint arrayev; avtomatizirani score ne pokaže nedovoljenih križanj/prekrivanj, render pa omogoča pregled glavnega toka in tehničnih koridorjev.
- **Status:** PARTIAL/BLOCKED — native XML, structural and traceability checks passed; rendered visual validation unavailable
- **Linked steps:** STEP-011, STEP-012, STEP-013

## Architecture and Approach
- Diagram tip: večstranski cross-functional swimlane/flowchart z arhitekturnim kontekstom in tehnično podatkovno stranjo.
- Dodatni diagram tip: enostranski »master flow« na zelo velikem platnu; horizontalni pasovi sledijo času, navpični koridorji pa ločijo poslovni tok, podatke/SQL, integracije in izhode.
- Primarni tok: levo proti desni; izjemne poti tečejo po ločenih spodnjih/zgornjih koridorjih.
- Swimlane-i: Operativa/uporabnik, BiZPIZ/EP, NPDPSS001000, UDG/DG, CMOD in obvestila.
- Oblike: procesi za izvajanje, diamanti samo za odločitve, cilindri za podatkovne shrambe, dokumentne oblike za XLSX/ZIP/PDF/email, rdeče poti za napake.
- Barve: modra storitev/proces, siva zunanji sistem, zelena uspeh/hramba, rumena odločitev/podatki, oranžna integracija, vijolična pravice, rdeča napaka/ročna obravnava.
- Ročno izdelan XML je primeren zaradi več strani, natančnih swimlane-ov, zgoščenih odločitev, opomb s SQL in kontroliranega routinga. Pred izdelavo je treba prebrati še podrobna pravila avtorstva XML iz `drawio-skill`.

## Execution Phases
1. **Analiza vira:** preberi in normaliziraj dokument, izloči entitete, korake, odločitve, klice in nejasnosti.
2. **Semantični model:** pripravi sledljiv procesni model, izhode in povezave med sistemi/podatki.
3. **Izdelava diagrama:** izdelaj večstranski XML z doslednim slogom, containmentom, robovi in legendami.
4. **Strukturna validacija:** preveri XML, draw.io pravila, ID-je, povezave, starše in layout.
5. **Vizualna validacija:** izvoz PNG, pregled berljivosti in popravki.
6. **Zaključek:** posodobi dokaze, status zahtev in končno oceno v tem planu.
7. **Razširjeni enostranski flow:** pripravi layout, izdelaj enostranski XML, ga strukturno validiraj in izvedi vizualni pregled oziroma dokumentiraj okoljsko omejitev.

## Step Tracker

### STEP-001 — Normaliziraj navodila NPDPSS001000 v sledljiv procesni inventar
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-001, REQ-004
- **Dependencies:** None
- **Objective:** Ustvari preverljiv povzetek vseh korakov, podatkovnih objektov, akterjev, sistemov in tehničnih klicev iz `.doc`.
- **Actions:** Identificiran je bil edini izvorni `.doc`; preverjeni so OLE/Windows-1250 metapodatki; vsebina je bila izločena s predhodnim `strings -el` izpisom in normalizirana v sledljiv inventar. Ločeni so NPDPSS001000 odseki, izven-scope XLSX odseki in zaključni NPLDSSEZ001000 fragment; popisani so koraki 2.a–7.g, izhodi, tabele/polja, procedure, SQL kontrole, vloge, integracije in odprta vprašanja.
- **Artifacts:** `NPDPSS001000-source-inventory.md`; izvorni dokument `NPDP - Navodila za programiranje - Shranjevanje CSD DPP v UDG NPDPSS001000.doc`.
- **Acceptance criteria:** Inventar pokriva vseh 18 strani/odsekov, vsebuje slovenske šumnike, vsak glavni element ima izvorno sled ali je označen kot odprto vprašanje/predpostavka; ne izdeluje diagrama.
- **Validation:** `file '<source>.doc'`; Python UTF-8/šumniki/preverjanje vseh oznak 2.a–7.g in ključnih tabel/procedur; ročni pregled inventarja glede na `/tmp/doc.txt` in odseke vira.
- **Evidence:** `file` je vrnil 18 strani, 4.073 besed, 23.222 znakov in Windows-1250. `NPDPSS001000-source-inventory.md` ima 191 vrstic/2.149 besed/15.817 bajtov; kontrolni Python skript je izpisal `artifact checks passed: UTF-8, Slovenian diacritics, 22 decision labels, required entities/procedures` z izhodno kodo 0. Inventar dokumentira omejitev OLE ekstrakcije in nejasno pravilo tipa 4.
- **Notes:** Nativni legacy `.doc` parser (antiword/LibreOffice) ni bil na voljo; inventar je semantično normaliziran iz preverjenega OLE `strings -el` izpisa, ne pa predstavljen kot nepreverjen dobesedni prepis. Nejasni deli so označeni v razdelku »Odprta vprašanja in tveganja za diagram«.

### STEP-002 — Modeliraj glavni paketni tok in tok posamezne PDF odločbe
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-002, REQ-003
- **Dependencies:** STEP-001
- **Objective:** Iz inventarja sestavi natančen graf odločitev od pravice in nove vloge do obdelave posamezne osebe.
- **Actions:** Modelirano je preverjanje `DPP_PDF_BJ`, odkrivanje nove vloge, inicializacija zadeve, razpakiranje ZIP, iteracija PDF datotek, vse kontrole 2.a–6.b, matrika 7.a–7.g, terminalni izhodi, statusne spremembe in vrnitev v paketno zanko.
- **Artifacts:** `NPDPSS001000-semantic-model.md` — 191 vrstic, 2.402 besed; vsebuje 107 identificiranih vozlišč, 47 eksplicitnih robov, pogoje, terminalne izhode in statusno tabelo.
- **Acceptance criteria:** Za vsako vejo so določeni pogoj, rezultat, ciljna tabela/status in naslednji korak; napake z različnimi opombami niso združene; paketna zanka je zaključena.
- **Validation:** Python preverjanje je potrdilo 0 manjkajočih referenc robov, vse zahtevane tehnične sledi/statusne vrednosti in prisotnost vseh oznak 2.a–7.g; ročni pregled modela glede na inventar.
- **Evidence:** `E-008`, `E-009`.
- **Notes:** Diagram še ni izdelan. Tip odločbe 4, celoten šifrant `TP_OPOMBA`, prejemnik e-pošte in manjkajoče preslikave faz ostajajo eksplicitno označeni kot odprta vprašanja.

### STEP-003 — Modeliraj izhode: strokovni delavec, avtomatska hramba, PIZ in mrtvi primeri
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-002, REQ-003
- **Dependencies:** STEP-002
- **Objective:** Prikaži vsa končna dejanja in pravilo preverjanja `DT_SMRT` pred dodelitvijo strokovnemu delavcu.
- **Actions:** Iz semantičnega modela je izdelana matrika 7.a–7.g, ločena matrika tehničnih/poslovnih napak, prioritetni algoritem izhodov, podmatrika `DT_SMRT` ter podmatrika AVT/PIZ zaključka. Eksplicitno so povezane vloge, klasifikacije, statusi, `ID_ZADEVA` in klic `DG.P_ZAKLJUCI_ZADEVO`.
- **Artifacts:** `NPDPSS001000-outcome-decision-matrix.md` — 84 vrstic, 7.949 bajtov; sledljivost do `P30`, `P31–P33`, `O01–O10` in izvornih odsekov.
- **Acceptance criteria:** Jasno so prikazani vloge `014-47-1`, `014-47-1-PIZ`, `014-47-1-SD`, `014-47-1-AVT`, veje 7.a–7.g, `DT_SMRT` pred SD, mrtvi izhod, statusi `SF_REZULTAT`/`DT_OBDELAVA`, klasifikacije/rešitve in zaključna procedura.
- **Validation:** Python preverjanje artefakta potrdi vse oznake 7.a–7.g, `DT_SMRT`, vse tri ciljne vloge, `DG.P_ZAKLJUCI_ZADEVO` z eksplicitnimi parametri ter statuse `SF_REZULTAT=1/2/NULL`; ročna primerjava s semantičnim modelom in inventarjem.
- **Evidence:** `E-010`, `E-011`.
- **Notes:** Virna izjema »mrtva oseba se avtomatsko zapre ne glede na napako« je ločena od primerov brez `SF_OSEBE`, ki se ne smejo prikazati kot mrtvi. Tip odločbe 4 ostaja označen kot odprto vprašanje.

### STEP-004 — Zasnuji večstransko vizualno postavitev in legendo
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-002, REQ-003, REQ-007
- **Dependencies:** STEP-002, STEP-003 — izpolnjeno (`DONE`/`PASSED`)
- **Objective:** Pretvori validirani semantični model in matriko izhodov v konkreten, pregledljiv layout načrt za večstranski draw.io diagram.
- **Actions:** Izdelan je šeststranski layout načrt z naslovom, namenom, canvas dimenzijami, swimlane-i, koordinatnimi koridorji, glavnimi/izjemnimi potmi, lokalnimi legendami, medstransko navigacijo, barvno semantiko, ID-shemo, containment pravili in routing pravili. Strani so: 01 sistemski kontekst, 02 paketni tok, 03 PDF kontrole, 04 izhodi 7.a–7.g, 05 podatki/SQL/procedure, 06 UDG/CMOD/PIZ/e-pošta. XML ni bil izdelan.
- **Artifacts:** `NPDPSS001000-layout-plan.md` (195 vrstic, 1.791 besed, 14.143 bajtov).
- **Acceptance criteria:** Vsaka od šestih strani ima naslov, namen, vsebino, swimlane-e in postavitev; glavni tok ter napake/ročne poti imajo ločene koridorje; legenda pokriva proces, odločitev, podatke, integracije, uspeh, napako, pravico in odprta vprašanja; ID-shema in parent-child containment sta eksplicitna; layout ne uvaja novih poslovnih pravil.
- **Validation:** Python preverjanje je potrdilo šest strani, najmanj šest swimlane sklopov, glavni/izjemni routing, barvno legendo, ID-shemo z `parent`, sledljivost REQ-002/003/007 ter odsotnost ciljnega `.drawio` XML. Preverjanje je zaključeno z izhodno kodo 0.
- **Evidence:** `E-013`, `E-014`.
- **Notes:** REQ-006 in končna vizualna validacija ostajata za STEP-006/007. Odprta vprašanja tipa odločbe 4, `TP_OPOMBA`, faz `DG.POT_ZADEVE` in prejemnika e-pošte so v layoutu označena z opombami. Naslednji izvedljivi korak je STEP-005.

### STEP-005 — Vključi podatkovni model, SQL/procedure in integracije
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-004, REQ-005
- **Dependencies:** STEP-001, STEP-004 — izpolnjeno (`DONE`/`PASSED`)
- **Objective:** Ustvari tehnični inventar, ki omogoča sledljiv prikaz podatkov, SQL kontrol, procedur, registracij, dokumentnega toka in poročanja brez izmišljanja izvajalnih podrobnosti.
- **Actions:** Izdelan je inventar objektov `EP.*`, `NP.*`, `DG.*`, CMOD queue in e-pošte; popisani so ključni predikati, statusi, procedure `DG.P_POISCI_ZADEVO`/`DG.P_ZAKLJUCI_ZADEVO`, registracije `SS.EVIDENTIRANJE_VLOG`, `DG.DOKUMENT`, `DG.POT_ZADEVE`, CMOD/PIZ klici ter semantika robov `read/write/update/call/message`. Nejasnosti so označene kot odprta vprašanja.
- **Artifacts:** `NPDPSS001000-technical-inventory.md` — 120 vrstic, 1.266 besed, 8.944 bajtov.
- **Acceptance criteria:** Inventar vsebuje vse tabele, procedure, SQL kontrole in integracije iz REQ-004/005; vključuje `ID_VRSTA_DOK=1341`, `DT_ZACETEK`, `SF_REZULTAT`, `DT_OBDELAVA`, `DT_SMRT`, registracije 86–89, CMOD queue in oba servisa; ZIP/PDF razlika in omejitve so eksplicitne.
- **Validation:** Python preverjanje ne-praznega UTF-8 artefakta, prisotnosti vseh zahtevanih entitet/predikatov/procedur/statusov/integracij in vseh štirih predhodnih artefaktov; ročna primerjava z inventarjem, matriko in layoutom.
- **Evidence:** `E-015`, `E-016`.
- **Notes:** Klici so dokumentacijska sled iz vira, ne dokaz izvedbe v okolju. Tip odločbe 4, celoten `TP_OPOMBA`, faze `DG.POT_ZADEVE` in prejemnik e-pošte ostajajo označeni kot odprta vprašanja. Naslednji izvedljivi korak je STEP-006.

### STEP-006 — Izdelaj nativni večstranski draw.io XML
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-006, REQ-007
- **Dependencies:** STEP-004, STEP-005 — izpolnjeno (`DONE`/`PASSED`)
- **Objective:** Ustvari končni uredljiv diagram na predvideni poti.
- **Actions:** Preberi `xml-authoring.md`; izdela XML s celicama `0`/`1`, unikatnimi ID-ji, stranmi, parent-child containmentom, geometrijo vozlišč/robov, HTML oznakami in ortogonalnimi povezavami.
- **Artifacts:** `NPDPSS001000-csd-dpp-udg-cmod.drawio` in samodejna `.bak` kopija pri spremembah.
- **Acceptance criteria:** Datoteka je ne-prazna, XML je well-formed, vse povezave ciljajo obstoječe celice, vsebine so uredljive in vse zahtevane strani obstajajo.
- **Validation:** `python3 drawio-skill/scripts/validate.py NPDPSS001000-csd-dpp-udg-cmod.drawio`; po potrebi `--score` in `edgeports.py`.
- **Evidence:** `E-017`, `E-018`, `E-019`.
- **Notes:** Ustvarjenih je šest strani z nativnimi swimlane containmenti, 112 unikatnimi ID-ji in 36 robovi; vsi robovi imajo razširjeno relativno geometrijo. Vizualni PNG pregled ostaja v STEP-007.

### STEP-007 — Izvozi, vizualno preglej in popravi diagram
- **Execution:** DONE
- **Validation:** PARTIAL — strukturni in avtomatizirani routing/preflight pregledi so PASSED; dejanski PNG/PDF vizualni pregled je BLOCKED zaradi manjkajočega rendererja.
- **Requirements:** REQ-006, REQ-007
- **Dependencies:** STEP-006 — izpolnjeno (`DONE`/`PASSED`)
- **Objective:** Dokazati, da diagram ni le sintaktično veljaven, temveč tudi berljiv.
- **Actions:** Preverjena je prisotnost draw.io CLI in alternativnih rendererjev; `drawio --version` je vrnil `exit 127`, zato izvoz PNG/PDF ni bil izvedljiv. Izvedeni so bili `validate.py`, `validate.py --strict`, `validate.py --score`, XML preflight šestih strani ter pregled robov, ID-jev, containmenta in geometrije. Diagram ni bil spreminjan, ker avtomatizirani pregledi niso pokazali napake in brez rendererja ni varno ugibati vizualnih popravkov.
- **Artifacts:** `NPDPSS001000-visual-validation.md`; `NPDPSS001000-csd-dpp-udg-cmod.drawio`.
- **Acceptance criteria:** Strukturni kriteriji so izpolnjeni; glavni tok in tehnična vsebina imata 6 ločenih strani, avtomatizirani pregled pa ne pokaže križanj, prekrivanj ali robov skozi vozlišča. Kriterij PNG/PDF izvoza in dejanske rasterizirane berljivosti ostaja nedokazan zaradi okoljske omejitve.
- **Validation:** `python3 drawio-skill/skills/drawio-skill/scripts/validate.py NPDPSS001000-csd-dpp-udg-cmod.drawio`; isti ukaz z `--strict`; isti ukaz z `--score`; Python XML preflight strani in `git diff --check`.
- **Evidence:** `E-020`, `E-021`, `E-022`.
- **Notes:** Ni nameščenega `drawio`/`draw.io`, `libreoffice`, `inkscape`, Chromium/Firefox ali `wkhtmltoimage`; zato ni bilo PNG/PDF artefaktov. Za popolno zaprtje REQ-007 je potreben renderer v zunanjem/ne-sandbox okolju in pregled vseh šestih strani. Naslednji izvedljivi korak je STEP-008 — končna sledljivost z jasno označenim delnim rezultatom.

### STEP-008 — Zaključi sledljivost, validacijo in oceno plana
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-001–REQ-007
- **Dependencies:** STEP-007 — izpolnjeno (`DONE`; validation partial)
- **Objective:** Primerjaj dejansko stanje z vsemi zahtevami in zaključi plan samo z objektivnimi dokazi.
- **Actions:** Preverjeni so artefakti, rendererji, validator izhodi, vizualni dokazni zapis, odprta vprašanja in izven-scope spremembe; posodobljeni so Evidence Log, Validation Matrix in Final Assessment.
- **Artifacts:** Posodobljen `PLAN.md` z objektivnimi dokazi, omejitvijo in remediation korakom.
- **Acceptance criteria:** Vse izvedljive zahteve imajo dokaz; nedokazana MUST zahteva je označena kot PARTIAL/BLOCKED; statusi in omejitve odražajo dejansko stanje.
- **Validation:** `command -v` preverjanje rendererjev, ponovitev `validate.py`/`--strict`/`--score`, končni trace zahtev → artefakt → ukaz.
- **Evidence:** `E-023`, `E-024`, `E-025`.
- **Notes:** REQ-007 ostaja delno validirana; ustvarjen je STEP-009 za zunanjo vizualno validacijo.

### STEP-009 — Izvedi vizualno validacijo v okolju z rendererjem
- **Execution:** BLOCKED
- **Validation:** BLOCKED
- **Requirements:** REQ-007
- **Dependencies:** STEP-008; draw.io CLI ali drug združljiv renderer v zunanjem okolju
- **Objective:** Izvoziti vseh šest strani v PNG/PDF in objektivno potrditi berljivost, odrezana besedila, kontrast, prekrivanja ter jasnost povezav.
- **Actions:** V okolju z rendererjem izvoziti strani 1–6, pregledati slike, po potrebi minimalno popraviti XML, nato ponoviti strukturni validator in `git diff --check`.
- **Artifacts:** Šest PNG/PDF izvozov in posodobljen `NPDPSS001000-visual-validation.md`; po popravkih posodobljen `.drawio`.
- **Acceptance criteria:** Vseh šest izvozov obstaja in je berljivih; ni odrezanih besedil, kritičnih prekrivanj, nejasnih puščic ali nedovoljenih križanj; strukturni validator ostane uspešen.
- **Validation:** Renderer version/command output, pregled vseh šestih izvozov, `validate.py`, `--strict`, `--score` in XML preflight.
- **Evidence:** Pending — renderer ni na voljo v trenutnem workspace-u.
- **Notes:** Blokirano zaradi okoljske omejitve, ne zaradi ugotovljene napake v XML.

- **E-017:** Prebrana referenca `resources/file_resources/xml-reference.md` pred izdelavo; uporabljena so pravila za unikatne ID-je, relativno geometrijo robov, `html=1`, containment in odsotnost waypoint arrayev.
- **E-018:** Ustvarjen `NPDPSS001000-csd-dpp-udg-cmod.drawio` z action=create; datoteka vsebuje šest strani (`01 Sistemski kontekst`, `02 Glavni paketni tok`, `03 PDF kontrole`, `04 Izhodi`, `05 Podatki SQL procedure`, `06 Dokumentni tok`), 112 unikatnih ID-jev, 36 robov in brez dangling referenc.
- **E-019:** `upsert_drawio_diagram action=validate` in `python3 drawio-skill/skills/drawio-skill/scripts/validate.py` sta vrnila uspeh: `0 error(s), 0 warning(s)`; `--score` je vrnil `0 through-vertex, 0 crossings, 0 overlaps`.
- **E-020:** Ustvarjen `NPDPSS001000-visual-validation.md`; dokumentira poskus preverjanja rendererja, šeststranski XML preflight, zahteve REQ-006/007 in omejitev brez PNG/PDF izvoza.
- **E-021:** `drawio --version` je vrnil `exit 127` (`drawio: not found`); preverjeni alternativni rendererji niso bili na PATH. Zato PNG/PDF izvoz ni bil izveden in ni bil ustvarjen lažen vizualni dokaz.
- **E-022:** `validate.py`, `validate.py --strict`, `validate.py --score`, Python preflight in `git diff --check` so uspešni: `0 error(s), 0 warning(s)`, `0 through-vertex, 0 crossings, 0 overlaps`, 6 strani z `mxGraphModel`, 112 ID-jev, 36 robov, 0 dangling/geometry napak.
- **E-023:** Renderer availability rechecked with `command -v` for drawio, draw.io, libreoffice, soffice, inkscape, Chromium, Firefox and wkhtmltoimage; all returned no path.
- **E-024:** Repeated structural validation exited 0: normal and strict `0 error(s), 0 warning(s)`; score `0 through-vertex, 0 crossings, 0 overlaps`.
- **E-025:** Final traceability review confirmed required artifacts exist and are non-empty; REQ-001–REQ-006 are evidenced, while REQ-007 remains PARTIAL/BLOCKED solely because rasterized visual evidence is unavailable.


### STEP-010 — Zasnuji enostranski master-flow layout
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-008, REQ-009, REQ-010
- **Dependencies:** STEP-001, STEP-002, STEP-003, STEP-004, STEP-005 — izpolnjeno (`DONE`/`PASSED`)
- **Objective:** Določiti konkretno enostransko postavitev, ki združi poslovni tok, podatke, tehnične klice, integracije in izhode na enem platnu.
- **Actions:** Izdelan je layout z enim platnom 13.600 × 5.800 px, šestimi vodoravnimi pasovi, stolpci C00–C31, glavnim M01–M34 tokom, napakami X/R/D/S, AVT/PIZ izhodi, podatkovnimi karticami T01–T11, SQL Q01–Q04, procedurami, registracijami, legendami, containmentom in routing pravili.
- **Artifacts:** `NPDPSS001000-single-page-layout-plan.md` — 197 vrstic, 16.054 bajtov.
- **Acceptance criteria:** Layout vsebuje vse korake 2.a–7.g, paketno zanko, vse zahtevane objekte/klice/izhode in eksplicitno strategijo proti prekrivanjem/križanjem; določa eno stran in ne uvaja novih poslovnih pravil.
- **Validation:** Python preverjanje je potrdilo `lines=197`, `bytes=16054`, `missing=[]` za vse oznake 2.a–7.g, zahtevane tabele, procedure, integracije, statuse in robne semantike `read/write/update/call/message`; pregledana je sledljivost do source inventory, semantic model, outcome matrix in technical inventory.
- **Evidence:** `E-026`, `E-027`.
- **Notes:** XML se v tem koraku ni izdeloval. STEP-011 je pripravljen kot naslednji izvedljivi korak.

### STEP-011 — Izdelaj enostranski nativni draw.io XML
- **Execution:** DONE
- **Validation:** PASSED — XML/strukturna validacija uspešna; vizualni render ostaja za STEP-013
- **Requirements:** REQ-008, REQ-009, REQ-010
- **Dependencies:** STEP-010 (`DONE`/`PASSED`)
- **Objective:** Ustvariti `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio` z vsemi elementi na eni strani.
- **Actions:** Prebrati aktualna XML pravila, izdelati eno `diagram` stran z unikatnimi ID-ji, parent-child containmentom, HTML oznakami, geometrijo vseh robov, ortogonalnim routingom, legendami in označenimi tehničnimi semantikami.
- **Artifacts:** `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio` in morebitna `.bak` kopija.
- **Acceptance criteria:** Datoteka je well-formed, ima točno eno stran, brez dangling endpointov/waypoint arrayev, vsebuje vse zahtevane vsebine in je uredljiva v draw.io.
- **Validation:** XML generator output, `upsert_drawio_diagram(action=validate)`, `validate.py`, `--strict`, `--score` in XML preflight. Ustvarjanje datoteke je bilo izvedeno pred validacijo; `action=create` ni bilo ponovno klicano nad že ustvarjenim artefaktom.
- **Evidence:** `E-028`, `E-029`, `E-030`.
- **Notes:** Enostranski XML je izdelan kot ločen artefakt; obstoječi šeststranski diagram ni bil spreminjan. STEP-012 je pripravljen kot naslednji izvedljivi korak za ločeno popolno sledljivostno/preflight poročilo.

### STEP-012 — Preveri popolno sledljivost in strukturni layout enostranskega diagrama
- **Execution:** DONE
- **Validation:** PASSED
- **Requirements:** REQ-008, REQ-009, REQ-010
- **Dependencies:** STEP-011 (`DONE`/`PASSED`)
- **Objective:** Objektivno dokazati, da enostranski diagram vsebuje celoten flow in tehnični inventar brez strukturnih napak.
- **Actions:** Izveden je namenski XML parser/preflight; preverjeni so count strani, vse M-kartice, kontrole 2.a–7.g, napake, ročne poti, izhodi, podatkovne/SQL/procedure kartice, registracije, ključna polja/statusi, sistemi/integracije, semantike robov, endpointi, starši, geometrija, unikatni ID-ji in waypoint pravila. Pri začetnem dobesednem trace pregledu so bile zaznane tri vsebinske skupine, zapisane z okrajšavami/rangiranjem; XML je bil minimalno dopolnjen z eksplicitnimi oznakami in ponovno validiran.
- **Artifacts:** `NPDPSS001000-single-page-validation.md`; posodobljen `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio`.
- **Acceptance criteria:** Vsi zahtevani elementi so najdeni, vsi robovi so veljavni, ni dangling referenc, `validate.py` in `--strict` sta uspešna, score ne pokaže nedovoljenih križanj/prekrivanj.
- **Validation:** `python3 /tmp/step012.py`; `upsert_drawio_diagram(action=validate)`; `validate.py --strict`; `validate.py --score`; `git diff --check`.
- **Evidence:** `E-031` začetni trace je našel manjkajoče eksplicitne oznake; `E-032` po minimalni dopolnitvi poroča `all_traceability_tokens_present=true`, 1 stran, 195 celic, 104 robove, 0 dangling/geometry napak in brez waypoint markup; `E-033` validator/upsert/score/diff so uspešni.
- **Notes:** Strukturna in vsebinska sledljivost sta PASSED. Dejanska vizualna berljivost še ni potrjena in ostaja v STEP-013.

### STEP-013 — Izvedi vizualno validacijo enostranskega master flowa in zaključi razširitev
- **Execution:** BLOCKED
- **Validation:** BLOCKED — renderer ni na voljo v workspace-u
- **Requirements:** REQ-010
- **Dependencies:** STEP-012 (`DONE`/`PASSED`); renderer je potreben za popolno validacijo
- **Objective:** Preveriti dejansko berljivost enega zelo gostega platna in po potrebi minimalno popraviti XML.
- **Actions:** Preveriti razpoložljiv renderer; ker ga ni, je bil namesto nepreverjenega renderiranja izveden ciljni layout refresh iz smernic `drawio-skill`: standardni horizontalni swimlane headers, enoten grid 10 px, večji medsebojni razmaki, dva urejena nivoja za glavni tok in tehnične kartice, ločeni exception/output koridorji, omejena legenda ter ortogonalni robovi z razporejenimi porti. Naknadni pregled containmenta je odkril, da so bili elementi L3/L4 zunaj premajhnih starševskih swimlane-ov in da je bil M07 zunaj glavnega pasu; to je bilo popravljeno izključno v enostranskem XML z večjim platnom in brez vsebinskih sprememb. Nato so bili ponovljeni vsi strukturni validatorji. PNG/PDF in rasteriziran pregled nista bila izmišljena.
- **Artifacts:** Posodobljen `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio`; `NPDPSS001000-single-page-validation.md` ostaja dokazni zapis. PNG/PDF izvoz ni ustvarjen, ker renderer ni na voljo.
- **Acceptance criteria:** Celoten flow je razpoznaven na eni strani, vsi kritični napisi so berljivi pri povečavi, ni kritičnih prekrivanj/odrezov; če renderer ni na voljo, je korak označen BLOCKED brez lažnih vizualnih trditev.
- **Validation:** Renderer command/version, pregled izvozov, `validate.py`, `--strict`, `--score`, XML preflight in `git diff --check`.
- **Evidence:** `E-034`, `E-035`, `E-036`, `E-037`, `E-038`, `E-039`.
- **Notes:** Renderer je še vedno nedosegljiv, zato je STEP-013 BLOCKED za rasteriziran vizualni dokaz. Na podlagi konkretnih `drawio-skill` primerov je bil layout ponovno reflowan izključno v enostranskem diagramu: podatki v treh vrstah, M01–M34 v šestih serpentinastih vrstah, izjeme/izhodi v štirih stolpcih, poročanje ločeno, naslov in legenda brez prekrivanja. Večstranski diagram ni bil spreminjan. Končni score je 0 prekrivanj, 0 križanj in 0 robov skozi vozlišča.

## Validation Matrix
| Requirement | Artifact/check | Status | Evidence |
|---|---|---|---|
| REQ-001 | Source traceability and content inventory | PASSED | E-006, E-018; source inventory and six-page diagram |
| REQ-002 | Main-flow and outcome pages | PASSED | STEP-002–004; E-018 |
| REQ-003 | Decision matrix/error branches | PASSED | STEP-002–004; E-018 |
| REQ-004 | Context/data/integration pages | PASSED | E-015, E-016, E-018 |
| REQ-005 | Procedure, SQL and configuration annotations | PASSED | E-015, E-016, E-018 |
| REQ-006 | `validate.py`, XML parse, draw.io openability | PASSED (structural; openability not runtime-tested) | E-017–E-022 |
| REQ-007 | PNG/PDF visual review and automated routing preflight | PARTIAL/BLOCKED | E-020–E-025; structural preflight passed, renderer unavailable; STEP-009 |
| REQ-008 | Single-page master-flow layout/XML | PASSED (content/structure; rendered visual pending) | E-026–E-033; STEP-012/013 |
| REQ-009 | Complete single-page data/technical traceability | PASSED (dedicated trace report; renderer-independent) | E-026–E-033; STEP-012 |
| REQ-010 | Single-page native validity and visual readability | PARTIAL/BLOCKED — native structure/trace PASSED; rendered visual review unavailable | E-026–E-036; STEP-013 |

## Dependencies
- Source `.doc` file and an extraction method supporting legacy OLE/Windows-1250.
- `drawio-skill` reference files and scripts.
- Python 3 and XML parser.
- Optional draw.io CLI for rendered visual validation.
- Large-canvas layout may exceed default zoom/readability; renderer and manual inspection are required.

## Risks
- Legacy `.doc` extraction may corrupt šumnike or omit embedded images/tables.
- Source includes a later unrelated section (`NPLDSSEZ1000`); it must not leak into NPDPSS001000 scope.
- Several source statements are terse/ambiguous; assumptions must be labelled.
- A very detailed diagram may become unreadable; multiple pages and technical notes mitigate this.
- Existing deleted artifacts cannot be used as authoritative output.

## Blockers
- **BLK-001 — Resolved.** Extraction and diagram generation completed.
- **BLK-002 — Active:** No draw.io/alternative renderer is installed or available on PATH; impact is inability to produce objective PNG/PDF evidence for REQ-007. Resolution: run STEP-009 in an environment with a compatible renderer.
- **BLK-003 — Active:** STEP-013 inherited the renderer limitation; do not mark visual acceptance passed without rendered evidence. Resolution: rerun STEP-013 in an environment with a compatible renderer.

## Deviations
- **DEV-001:** Planned PNG/PDF validation could not be executed in the current sandbox because no renderer is available. Structural validation was retained; no visual claims were fabricated.
- **DEV-002:** Initial STEP-013 environment check was BLOCKED and made no XML changes; the later user-requested correction round is separately evidenced by E-040/E-041 and remains BLOCKED only for rasterized visual proof.

## Evidence Log
- **E-001:** Workspace listing found the source document and `drawio-skill` repository; command completed with exit code 0.
- **E-002:** `file` identified the source as a legacy Word OLE document, 18 pages, 4073 words, Windows code page 1250.
- **E-003:** Draw.io XML reference was read from `resources/file_resources/xml-reference.md`; generation/validation constraints recorded above.
- **E-004:** Preliminary `strings -el` extraction at `/tmp/doc.txt` exposed the core process, tables, procedures, error codes, and CMOD handoff; not yet sufficient as final evidence because character decoding must be checked.
- **E-005:** Current git status reports prior target diagram/backup/plan paths as deleted; no current generated diagram is accepted until recreated and validated.
- **E-006:** Created `NPDPSS001000-source-inventory.md` (191 lines, 2,149 words, 15,817 bytes) with normalized Slovenian diacritics, scope separation, full process/decision inventory, data/procedure/integration inventory, and explicit open questions. Python artifact check passed with exit code 0; verified 22 decision labels (2.a–7.g) and all required entities/procedures.
- **E-007:** Source fingerprint re-run with `file` confirmed 18 pages, 4,073 words, 23,222 characters, Windows-1250. Legacy parser availability check found no `antiword`, `catdoc`, `libreoffice`, or `pandoc`; this limitation is recorded in STEP-001 and the inventory.

- **E-008:** Created `NPDPSS001000-semantic-model.md` (191 lines, 2,402 words) with separate package/PDF flows, 107 node IDs, explicit edge table, 2.a–7.g decision matrix, terminal output rules, status transitions, error messages and open questions. Diagram generation was intentionally not performed.
- **E-009:** Semantic-model validation command exited 0: `107 node IDs`, `47 edge rows`, `missing endpoints: []`, `missing required traces: []`, `semantic model validation passed`. Confirmed no `*.drawio*` artifact exists in workspace root at this step.
- **E-010:** Created `NPDPSS001000-outcome-decision-matrix.md` (84 lines, 7,949 bytes) with 7.a–7.g outcome mapping, error matrix, DT_SMRT precedence, role mappings, status contract and `DG.P_ZAKLJUCI_ZADEVO` call.
- **E-011:** Artifact validation exited 0: `missing checks: []`, `matrix validation passed`; checked all 7 decision labels, `DT_SMRT`, `014-47-1-PIZ`, `014-47-1-SD`, `014-47-1-AVT`, explicit conclusion procedure and `SF_REZULTAT` values 1/2/NULL.

- **E-012:** Workspace inspection after STEP-003 found all three prerequisite markdown artifacts present and non-empty, no target `*.drawio*` file in the workspace root, and no active blocker preventing STEP-004. `git status --short` confirms the target diagram and backup remain deleted/unavailable; inspection commands exited 0.

- **E-013:** Created `NPDPSS001000-layout-plan.md` (195 lines, 1,791 words, 14,143 bytes). The artifact defines six pages, page purposes, canvas dimensions, swimlanes, main/exception corridors, local/global legends, containment, ID naming, navigation and open-question annotations.
- **E-014:** Python layout validation completed with exit code 0: six page headings, at least six swimlane sections, routing terms, legend categories, ID/parent scheme, REQ-002/003/007 trace terms, and absence of `NPDPSS001000-csd-dpp-udg-cmod.drawio` were all confirmed. No XML was generated in STEP-004.
- **E-015:** Created `NPDPSS001000-technical-inventory.md` (120 lines, 1,266 words, 8,944 bytes) with 11 data/integration objects, 7 SQL controls, procedure signatures/calls, registrations 86–89, document/pot zadeve details, CMOD/PIZ/e-mail flow, status trace and open technical questions.
- **E-016:** Python validation exited 0: `technical inventory validation passed`, `bytes=8944 lines=120 missing=[]`; confirmed all REQ-004/005 entities, fields, predicates, procedures, queue/services and semantic edge labels, plus presence of all prerequisite artifacts.

- **E-026:** Created `NPDPSS001000-single-page-layout-plan.md`; file validation passed with `lines=197`, `bytes=16054`, `missing=[]`. The check covered 2.a–7.g, all required tables/fields and procedures, CMOD/PIZ services, status fields and `read/write/update/call/message` semantics.
- **E-027:** Manual traceability review confirmed the layout explicitly maps M01–M34, X01–X04, R01–R06, D01/S01/S02, A01–A09, P01–P05, T01–T11 and Q01–Q04 to the five prerequisite inventories. XML was not generated in STEP-010.
- **E-028:** Created `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio` as a separate native draw.io XML artifact. XML preflight reported `pages=1`, `cells=195`, `unique=195`, `edges=104`, `duplicates=[]`, `missing=[]`; the six swimlane lanes, one title/legend area, main M01–M34 flow, exception/output corridors, data cards, SQL/procedure cards and reporting area are present.
- **E-029:** `upsert_drawio_diagram action=validate` returned `Draw.io XML is valid according to enforced reference rules.`; `validate.py` and `--strict` returned `0 error(s), 0 warning(s)`; `--score` returned `0 through-vertex, 0 crossings, 0 overlaps`. All edges have relative `mxGeometry`; no manual waypoint arrays were used.
- **E-030:** `git diff --check` passed and the existing six-page `NPDPSS001000-csd-dpp-udg-cmod.drawio` was not modified. Actual PNG/PDF rendering was not claimed; renderer availability remains a STEP-013 concern.

- **E-031:** Prvi namenski dobesedni trace preflight je objektivno zaznal manjkajoče eksplicitne oznake `3.b`, `7.b/7.c/7.e/7.f`, `A02`, `P05`, `SF_ODLOCBA_BRANA`, `SF_DD_SKLEP_ODLOCBA`, `ZPIZCPR`/polnega PIZ klica ter `e-pošta`/`SF_REZULTAT=1`; zato začetni preflight ni bil sprejet kot PASS.
- **E-032:** Izvedena minimalna dopolnitev obstoječih XML vrednosti brez spremembe grafične strukture; ponovljeni trace poroča `all_traceability_tokens_present=true`, 1 stran, 195 celic, 104 robove, unikatne ID-je, 0 manjkajočih endpointov, 0 robov brez geometrije in brez ročnega waypoint markupa.
- **E-033:** `upsert_drawio_diagram(action=validate)` je vrnil uspeh; `validate.py --strict` je vrnil `0 error(s), 0 warning(s)`; `--score` je vrnil `0 through-vertex, 0 crossings, 0 overlaps`; `git diff --check` je uspešen.
- **E-034:** STEP-013 renderer probe checked `drawio`, `draw.io`, `libreoffice`, `soffice`, `inkscape`, `chromium`, `chromium-browser`, `google-chrome`, `firefox` and `wkhtmltoimage`; none resolved via `command -v`, and the probe exited with no available renderer.
- **E-035:** PNG/PDF export and rasterized inspection were not executed because no compatible renderer was available; no visual readability claim was made and the six-page diagram was not modified.
- **E-036:** Repeated single-page structural checks passed after the environment probe: normal/strict validation `0 error(s), 0 warning(s)`; score `0 through-vertex, 0 crossings, 0 overlaps`; existing validation artifact remains consistent.
- **E-037:** Prebrani so `resources/file_resources/xml-reference.md`, `drawio-skill/skills/drawio-skill/references/xml-authoring.md`, `SKILL.md` in primeri `drawio-skill/assets/workflow.drawio` ter drugi asseti; smernice zahtevajo dominantno bralno smer, grid, večje razmike, vidne swimlane meje, omejeno barvno semantiko in ortogonalne robove. Mapa `drawio-skill/asserts` v workspace-u ne obstaja; uporabljeni so razpoložljivi `assets/`, `references/` in `scripts/` v repozitoriju.
- **E-038:** Izveden je bil ciljni reflow izključno nad `NPDPSS001000-csd-dpp-udg-cmod-single-page.drawio`: canvas je nastavljen na `10600 × 4850`, pasovi imajo horizontalne naslove, glavni M01–M34 je razporejen v dva nivoja, vhodne/SQL/procedure kartice v urejene vrstice, napake/ročne poti in izhodi v ločene koridorje, legenda je zmanjšana in naslov/legenda se ne prekrivata. Poslovne oznake in celice niso odstranjene.
- **E-039:** Prvi ciljni reflow je bil izveden na podlagi smernic in je bil nato zavrnjen kot nezadosten, ker je score pokazal 19 prekrivanj.
- **E-040:** Druga korekcija je izključno nad enostranskim diagramom: platno `6200 × 5800`, podatkovne kartice v treh vrstah, M01–M34 v šestih serpentinastih vrstah, napake/izhodi v štirih stolpcih, ločeno poročanje in naslov/legenda brez prekrivanja. Večstranski diagram ni bil spreminjan.
- **E-041:** Končna validacija po korekciji: `validate.py` in `--strict` `0 error(s), 0 warning(s)`; `--score` `score=0 (0 through-vertex, 0 crossings, 0 overlaps)`; XML preflight `pages=1, cells=195, edges=104, arrays=0`; `upsert_drawio_diagram(action=validate)` je vrnil validen XML; `git diff --check` je uspešen.
- **E-042:** Ponovni layout/containment pregled je našel konkretne napake v predhodnem reflowu: `M07` je bil na `x=10390` zunaj `lane_main`, elementi spodnjih vrst L3/L4 pa so segali čez višino starševskih swimlane-ov. Popravljeno izključno v enostranskem XML: `M07 x=4980`, L3/L4 višina `1300`, L4/L5 prestavljena na `y=4450/5850`, canvas `6200 × 6700`, kontejnerji `pointerEvents=0`; poslovna vsebina in večstranski diagram sta nespremenjena.
- **E-043:** Po korekciji je containment preflight potrdil `0` elementov zunaj matičnega swimlane-a; `upsert_drawio_diagram(action=validate)`, normalni/strict validator, score in `git diff --check` so uspešni: `0 error(s), 0 warning(s)`, `score 0`, `0 through-vertex`, `0 crossings`, `0 overlaps`.
- **E-044:** Renderer probe je ponovno preveril `drawio`, `draw.io`, `libreoffice`, `soffice`, `inkscape`, Chromium/Chrome, Firefox in `wkhtmltoimage`; noben executable ni bil najden. PNG/PDF in dejanski rasterizirani vizualni pregled zato nista bila izvedena.


## Change Log
- **2026-06-15:** Created active execution plan after workspace inspection and source identification.
- **2026-06-15:** Completed STEP-001; added `NPDPSS001000-source-inventory.md`, validated source fingerprint and artifact structure, documented legacy `.doc` extraction limitation and unresolved type-4 mapping.
- **2026-06-15:** Completed STEP-002; added and validated `NPDPSS001000-semantic-model.md` without creating the draw.io diagram.
- **2026-06-15:** Completed STEP-003; added and validated `NPDPSS001000-outcome-decision-matrix.md` covering 7.a–7.g, DT_SMRT precedence, SD/PIZ/AVT roles and `DG.P_ZAKLJUCI_ZADEVO`; diagram generation remains intentionally deferred.
- **2026-06-15:** Po pregledu workspace-a potrjeni predpogoji za STEP-004; trije analitični artefakti obstajajo in so ne-prazni, ciljni `.drawio` pa še ne obstaja. STEP-004 je nastavljen na `READY`; diagram se v tem pregledu ni izdeloval.
- **2026-06-15:** Completed STEP-004; created and validated the six-page layout plan with legends, swimlanes, corridors, containment and ID/routing rules. STEP-005 is now the next executable step; XML generation remains deferred.
- **2026-06-15:** Completed STEP-005; created and validated `NPDPSS001000-technical-inventory.md` with data model, SQL controls, procedures, registrations, UDG/CMOD/PIZ/document flow and reporting traceability. STEP-006 is now READY; XML generation remains deferred.
- **2026-06-15:** Completed STEP-006; read draw.io XML authoring rules, created `NPDPSS001000-csd-dpp-udg-cmod.drawio` with six pages, validated it with `upsert_drawio_diagram` and `validate.py`, and set STEP-007 to READY for visual export/review.
- **2026-06-15:** Completed STEP-007 execution; created the visual-validation record and ran structural/routing preflight. PNG/PDF export is blocked by the absent draw.io CLI, so REQ-007 remains PARTIAL and STEP-008 is READY for final traceability/assessment.
- **2026-06-15:** Completed STEP-008 final traceability review. Renderer recheck found no executable; structural validation remains green. Added BLK-002 and STEP-009 remediation. Final result is INCOMPLETE due to unresolved REQ-007.
- **2026-06-15:** User requested an additional one-page, fully detailed master flow. Added REQ-008–REQ-010 and STEP-010–STEP-013; STEP-010 is the next executable action.
- **2026-06-15:** Completed STEP-010; created and validated the detailed single-page layout plan with M01–M34 main flow, all 2.a–7.g branches, data/SQL/procedure/integration cards, status semantics, containment and routing rules. STEP-011 is READY; XML generation remains deferred to that step.
- **2026-06-15:** Completed STEP-011; created the separate one-page native XML master flow, validated it with `upsert_drawio_diagram`, `validate.py`, `--strict`, `--score`, XML preflight and `git diff --check`. STEP-012 was READY for dedicated complete traceability validation; visual rendering remained for STEP-013.
- **2026-06-15:** Completed STEP-012. Initial exact-token trace found abbreviated labels; the XML was minimally amended, then traceability, draw.io validation, strict validation, score and diff checks passed. STEP-013 is READY; rendered visual validation remains pending because renderer availability is not yet established.
- **2026-06-15:** STEP-013 je bil ponovno izveden na zahtevo uporabnika. Pregledani so bili `drawio-skill` asseti in XML smernice; prvi reflow je bil zavrnjen zaradi 19 prekrivanj, nato je bil enostranski diagram ponovno razporejen v zračne vrstice/stolpce. Končni structural/strict/score/diff pregledi so zeleni; renderer ostaja nedosegljiv in vizualni PNG/PDF pregled ni potrjen. Dodana sta E-040–E-044; večstranski diagram ni bil spreminjan.

## Final Acceptance Checklist
- [x] Source was inspected and NPDPSS001000 scope separated from unrelated material.
- [ ] All MUST requirements are linked to a fully validated artifact; visual REQ-007/REQ-010 evidence remains pending.
- [x] Main process and all material exception branches are visible.
- [x] Systems, tables, procedures, SQL controls, configuration and CMOD handoff are traceable.
- [x] `NPDPSS001000-csd-dpp-udg-cmod.drawio` exists and is non-empty.
- [x] XML and draw.io structural validation passes.
- [ ] Rendered diagram has no critical layout defects and is readable; renderer unavailable.
- [ ] All mandatory steps are fully validated; STEP-009 and STEP-013 are BLOCKED pending renderer.
- [ ] No active blocker remains; BLK-002 and BLK-003 are active and the renderer limitation is documented.
- [x] Additional one-page master-flow diagram exists and passes structural plus dedicated traceability validation; rendered visual validation remains in STEP-013.

## Final Assessment
**INCOMPLETE** — The existing six-page diagram and analytical artifacts are complete; structural validation and traceability passed. The one-page master flow was visually reflowed using the available drawio-skill authoring guidance and now passes structural overlap/crossing checks, but STEP-013 remains BLOCKED because no compatible renderer is installed or available on `PATH`; PNG/PDF export and rasterized visual review were not performed. REQ-008 and REQ-009 are evidenced; REQ-010 remains PARTIAL/BLOCKED for rendered visual readability only. No claim of rasterized visual readability is made.
