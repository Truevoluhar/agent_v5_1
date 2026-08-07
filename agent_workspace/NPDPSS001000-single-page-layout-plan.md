# NPDPSS001000 — enostranski master-flow layout plan

## 1. Namen, obseg in oblikovno načelo

Ta načrt določa eno samo, zelo veliko draw.io platno za celoten proces NPDPSS001000. Diagram je namenjen razvijalcu/integratorju in testerju: poslovni tok ostane neprekinjen in sledljiv od zagona do poročila, tehnični podatki in klici pa so prikazani kot pripeti koridorji ob ustreznih korakih.

Diagram ne nadomešča šeststranskega diagrama; je dodatni »master view«. Ne uvaja novih pravil. Nejasnosti iz vira so prikazane kot odprta vprašanja.

**Osnovno načelo:** en glavni tok teče levo → desno v srednjem pasu. Zgornji pas vsebuje vhodne sisteme, podatkovne shrambe in SQL preglede; spodnji pas vsebuje napake, ročno obravnavo, smrtno kontrolo, AVT/PIZ/CMOD zaključke in poročanje. Robovi med pasovi so kratki in označeni s semantiko.

## 2. Platno in mreža

- **Strani:** natanko 1 `diagram`, naslov »NPDPSS001000 — celoten enostranski master flow«.
- **Predlagana velikost:** 13.600 × 5.800 px; canvas je namenoma širok in visok, da se ohrani celoten tok brez druge strani.
- **Mreža:** 20 px; vozlišča na mreži; 40 px horizontalni razmik med procesnimi stebri.
- **Glavni stolpci:** C00–C25, vsak približno 500 px; izjemni tokovi so v istem stolpcu kot sprožilni korak.
- **Glavni tok:** y=1.250–2.250; puščice levo → desno.
- **Podatkovno/SQL območje:** y=300–1.100.
- **Izjemni, ročni in terminalni izhodi:** y=2.450–4.850.
- **Legenda in odprta vprašanja:** x=11.250–13.350, y=4.900–5.600; legenda je ločena od toka.
- Vsa vozlišča imajo dovolj notranjega odmika; dolge opombe so razbite v največ 4–6 vrstic HTML besedila.

## 3. Swimlane-i / vodoravni pasovi

| Pas | Y območje | Namen | Barva |
|---|---:|---|---|
| L0 — Naslov/legenda | 0–260 | naslov, verzija, oznake robov, barvna legenda | temno modra |
| L1 — Vhodni sistemi in podatki | 300–1.100 | BiZPIZ/EP, ZIP omejitve, NP tabele, SQL kontrole | siva/rumena |
| L2 — NPDPSS001000 glavni proces | 1.250–2.250 | zagon, pravica, paket, PDF zanka, kontrole 2.a–6.b, matrika | modra |
| L3 — Napake in ročna obravnava | 2.450–3.350 | napake z `SF_REZULTAT=2`, SD, razlika mrtva/neznana oseba | rdeča/oranžna |
| L4 — UDG/CMOD/PIZ izhodi | 3.550–4.450 | AVT, PIZ, dokument, pot zadeve, CMOD, servisi | zelena/vijolična |
| L5 — Paketni zaključek in poročanje | 4.550–4.850 | agregacija, Excel, e-pošta, naslednja vloga, konec | zelena/siva |

Swimlane-i so pravi `swimlane`/`mxCell` vsebniki z vsemi otroškimi vozlišči pod ustreznim parentom. Podatkovne kartice so v L1, tudi če so z robom povezane v L2–L4.

## 4. Globalna vizualna semantika

- **Modra zaokrožena oblika:** proces NPDPSS001000.
- **Vijolični diamant:** pravica ali druga poslovna odločitev.
- **Rumeni/olivni cilindri:** tabela, podatkovni zapis ali statusna pogodba.
- **Siva zunanja oblika:** BiZPIZ, EP, UDG/DG, zunanji servis.
- **Zelena oblika:** uspešna hramba, PIZ ali avtomatski zaključek.
- **Rdeča oblika:** napaka ali nedokončan primer; vsebuje dobesedno `TX_OPOMBA`.
- **Oranžna oblika:** strokovni delavec, ročna obravnava ali razdelilnik.
- **Črtkana obroba/opomba:** odprto vprašanje, ne potrjeno pravilo.
- **Robovi:** `read` siva, `write/update` modra, `call` vijolična, `message` oranžna, poslovni tok temno modra, napaka rdeča.
- Na vsakem razcepu so oznake `DA`, `NE`, `0`, `>1`, `1`, `7.a`–`7.g` ali konkretni pogoj; rob brez oznake je dovoljen samo pri zaporednem koraku.

## 5. Glavni end-to-end koridor (L2)

| ID | Stolpec | Vozlišče | Vsebina/izhodi | Naslednji robovi |
|---|---|---|---|---|
| M01 | C00 | Zagon obdelave | Operativa zažene NPDPSS001000 | M02 |
| M02 | C01 | Pravica `DPP_PDF_BJ` | odločitev uporabniške pravice | NE→M03; DA→M04 |
| M03 | C02 | Ustavitev brez pravice | `uporabnik nima pravice`; konec brez paketa | terminal |
| M04 | C02 | Poišči novo eVlogo/ZIP | EP join, `SY_TISP <> 'B'`, izloči že obdelane v NP | NE→M05; DA→M06 |
| M05 | C03 | Ni nove priloge | ni nove obdelave; konec zagona | terminal |
| M06 | C03 | Izberi naslednjo vlogo/ZIP | naslednja neprenesena/neobdelana priloga | M07 |
| M07 | C04 | Evidentiraj osnovno eVlogo | `014-47-1`, CSDLJ, klas. `10390`, splošno, ostalo iz PIZ, `DT_PREJEMA` | M08 |
| M08 | C05 | `DG.P_POISCI_ZADEVO` — osnovna | `('DAVČNA ŠTEVILKA CSD LJUBLJANA','P','014-47-1',NULL,...,GUID)` → `ID_ZADEVA` | M09 |
| M09 | C06 | Posodobi `DG.ZADEVA` | `DT_ZACETEK := DT_PREJEMA`, če `SY_TISP <> 'B'` | M10 |
| M10 | C07 | Razpakiraj ZIP | PDF za obdelavo; ne-PDF ignoriraj; ZIP ostane v EP | M11 |
| M11 | C08 | Še PDF v paketu? | paketna zanka po datotekah | DA→M12; NE→M30 |
| M12 | C09 | Začni eno PDF odločbo | ustvari/posodobi zapis `NP.CSD_DPP_PDF` | M13 |
| M13 | C10 | PDF berljiv? | parser lahko bere vsebino | NE→X01; DA→M14 |
| M14 | C11 | Preberi prvo 13-mestno številko | kandidatni EMŠO iz besedila PDF | M15 |
| M15 | C12 | Shrani `SF_EMSO` — 2.a | zapis v `NP.CSD_DPP_PDF` | M16 |
| M16 | C13 | EMŠO prebran? — 2.b | `SF_EMSO IS NULL`? | NE→X02; DA→M17 |
| M17 | C14 | EMŠO = ime datoteke? — 2.c/2.d | `SF_EMSO = TX_DATOTEKA` | NE→M18; DA→M19 |
| M18 | C15 | Označi `EMŠO ni enak` — 2.c | napaka ostane; obvezno poišči osebo po EMŠO iz dokumenta | M19 |
| M19 | C16 | Poišči `SF_OSEBE` — 3.a, 3.b, 3.c | `DG.IDENTIFIKATOR`, tipi 1/9, aktiven, dolžina 13 | 0→X03; >1→X04; 1→M20 |
| M20 | C17 | Shrani enolično osebo — 3.c | `SF_OSEBE`; preveri predhodni neusklajeni EMŠO | M21 |
| M21 | C18 | Je bil EMŠO neusklajen? — 3.d | prejšnja napaka `EMŠO ni enak` | DA→R01; NE→M22 |
| M22 | C19 | Prepoznaj tip odločbe — 4.a | ključni stavki → `SF_ODLOCBA_BRANA`; tip 4 odprt | M23 |
| M23 | C20 | Tip prepoznan? — 4.b | `SF_ODLOCBA_BRANA=0` če ni | NE→R02; DA→M24 |
| M24 | C21 | Vhodni tip = prebrani? — 4.c/4.d | `SF_DD_SKLEP_ODLOCBA = SF_ODLOCBA_BRANA` | NE→R03; DA→M25 |
| M25 | C22 | Najdi preteklo CSD obdelavo — 5.a/5.b | `NP.CSD_DPP_OBDELAVA`, `SY_TISP <> 'B'` | NE→R04; DA→M26 |
| M26 | C23 | Obstaja uspešna odločba drugega tipa? — 6.a/6.b | isti `SF_OSEBE`, drug tip, `SF_REZULTAT <> 2` | DA→R05; NE→M27 |
| M27 | C24 | Matrika `DD_SKLEP_ODLOCBA + TP_OPOMBA` | en diamant z notranjimi vrsticami 7.a–7.g | 7.a/b/c/e/f→A01; 7.d→P01; 7.g/drugo→R06 |
| M28 | C25 | Zapiši rezultat primera | `SF_REZULTAT`, `ID_ZADEVA`, `TX_OPOMBA`, `DT_OBDELAVA` | M11 |
| M29 | C26 | Vrnitev v paketno zanko | konec ene PDF obdelave | M11 |
| M30 | C27 | Zaključi paket | agregira vse PDF rezultate | M31 |
| M31 | C28 | Ustvari Excel rezultat | vsa zahtevana polja po osebi | M32 |
| M32 | C29 | Sestavi/pošlji e-pošto | ZIP, datum, tip, tabela, št. primerov; prejemnik odprt | M33 |
| M33 | C30 | Naslednja neobdelana vloga/ZIP? | EP join, brez ID-ja v NP | DA→M06; NE→M34 |
| M34 | C31 | Konec paketnega cikla | končni terminal celotnega zagona | terminal |

## 6. Napake in SD-koridor (L3)

| ID | Povezava iz | Vozlišče | Obvezna vsebina | Povratek |
|---|---|---|---|---|
| X01 | M13 NE | PDF ni berljiv | `SF_REZULTAT=2`, `TX_OPOMBA='PDF ni berljiv'`, `DT_OBDELAVA=timestamp`; ne preverjaj smrti | M28 |
| X02 | M16 NE | EMŠO ni bil prebran | `SF_EMSO=NULL`, `SF_REZULTAT=2`; brez SD in brez AVT zaključka | M28 |
| X03 | M19 0 | Oseba je neznana | `SF_OSEBE=NULL`, `SF_REZULTAT=2`; brez SD in brez avtomatskega zaključka | M28 |
| X04 | M19 >1 | Neurejeni identifikatorji | `SF_OSEBE=NULL`, `SF_REZULTAT=2`; brez SD in brez avtomatskega zaključka | M28 |
| R01 | M21 DA | SD zaradi neusklajenega EMŠO | nadaljuj v kontrolo smrti; `014-47-1-SD` samo če oseba živa | D01 |
| R02 | M23 NE | Tip odločbe neznan | `SF_ODLOCBA_BRANA=0`, virna opomba, `SF_REZULTAT=2`; znana oseba gre v smrtno kontrolo | D01 |
| R03 | M24 NE | Tip ni enak dokumentu | virna opomba, `SF_REZULTAT=2`; znana oseba gre v smrtno kontrolo | D01 |
| R04 | M25 NE | Ni v predhodnih CSD obdelavah | virna opomba, `SF_REZULTAT=2`; znana oseba gre v smrtno kontrolo | D01 |
| R05 | M26 DA | Prejeta druga odločba | `Za to osebo smo že prej prejeli odločbo`; `SF_REZULTAT=2` | D01 |
| R06 | M27 7.g | Vse druge kombinacije | strokovni delavec po razdelilniku; pred tem smrtna kontrola | D01 |
| D01 | R01/R02/R03/R04/R05/R06 | `DG.OSEBA.DT_SMRT`? | če obstaja: mrtvi primer, brez SD naloge; če ne: živa oseba → SD | DA→A02; NE→S01 |
| S01 | D01 NE | Ustvari SD zadevo | `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-SD',NULL,...,GUID)`, klas. 10343, razdelilnik | S02 |
| S02 | S01 | Zapiši SD rezultat | `ID_ZADEVA`, `DT_ZACETEK=DT_PREJEMA`, napaka/opomba, `DT_OBDELAVA` | M28 |
| A02 | D01 DA | Mrtva oseba | ne glede na predhodno napako; brez SD; avtomatsko zapiranje | A03 |
| A03 | A02 | AVT zaključek mrtvega primera | uporabi AVT dokumentni/zapiralni tok; ohrani `DT_SMRT` in predhodno napako | M28 |

## 7. Avtomatska hramba in PIZ koridor (L4)

### 7.1 AVT — veje 7.a, 7.b, 7.c, 7.e, 7.f

- **A01:** Vhod iz M27 za `1/08`, `2/(03 ali 08)`, `3/08`, `5/07`, `6/07`.
- **A04:** `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-AVT',NULL,...,GUID)` → `ID_ZADEVA`; klasifikacija `10343`, splošno, dolgotrajna oskrba.
- **A05:** Vstavi PDF v `DG.DOKUMENT`; `DG.DOKUMENT_SEQ.NEXTVAL`, `ID_VRSTA_DOK=1341`, `ID_FORMAT=3`, `ID_STATUS=2`; naziv = `LEFT(TX_ZIP, CHARINDEX('_',TX_ZIP)-1)`.
- **A06:** Vstavi `DG.POT_ZADEVE`; brez PVI; virno navedene faze 2/5/6/25, `ID_POSTOPEK=25`, `ID_NACIN_RES=271`, `SF_KONTROLA 0/1`; popolno mapiranje je odprto.
- **A07:** `Q.SF.CM.LOAD.PDF.SIGN.IN` prejme PDF sporočilo; ZIP se ne pošilja neposredno.
- **A08:** `DG.P_ZAKLJUCI_ZADEVO(ID_ZADEVA,3,15248,10,4676,NULL,NULL,NULL)`; rešitev »rešitev brez akta«, brez PVI.
- **A09:** zapiši `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA`; povratek M28.

### 7.2 PIZ — veja 7.d

- **P01:** `DD_SKLEP_ODLOCBA=4`; `TP_OPOMBA` pravilo je v viru nepopolno — označi kot odprto.
- **P02:** registracija `SS.EVIDENTIRANJE_VLOG` ID 87, vloga `014-47-1-PIZ`, UDG; `ID_SIGN_ZNAK` po registraciji.
- **P03:** bazen `DO-PONOVNO IZPLAČILO PO MIROVANJU`, klasifikacija `10343`, splošno reševanje, dolgotrajna oskrba.
- **P04:** `NPPZSS001000.insertPzIzbor` → `ZPIZCPR/setObvestiloWS`; klica sta označena `call`, povratni protokol ni določen.
- **P05:** zapiši `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA`; povratek M28.

## 8. Podatkovne kartice in tehnični koridor (L1)

Kartice so v zgornjem pasu, z oznako objekta, ključnimi polji, operacijo in povezavo na korake. V diagramu ne smejo biti skrite samo v legendi.

| ID kartice | Objekt | Ključna vsebina | Robovi |
|---|---|---|---|
| T01 | `EP.VLOGE_ODDANE` | `ID_VLOGE_ODDANE`, `SF_OSEBA` | `read` → M04/M33 |
| T02 | `EP.PRIPONKE_ODDANE` | `ID_VLOGE_ODDANE`, ZIP, `SY_TISP`; ZIP ostane v EP | `read` → M04/M10 |
| T03 | `NP.CSD_DPP_PDF` | vsi zapisi: identiteta, ZIP/datoteka, EMŠO, oseba, tip, zadeva, rezultat, opomba, smrt | `read`, `write/update` ↔ M12–M29 |
| T04 | `NP.CSD_DPP_OBDELAVA` | `SF_EMSO`, `TP_OPOMBA`, `DT_SEZNAM`, `ST_SEZNAM`, `SY_TISP`, `SF_REZULTAT` | `read` → M25/M27 |
| T05 | `DG.IDENTIFIKATOR` | tipi 1/9, `SF_IDENT`, `SF_OSEBE`, aktiven, `SY_TISP` | `read` → M19 |
| T06 | `DG.OSEBA` | `SF_OSEBE`, `DT_SMRT`, `SY_TISP` | `read` → D01; `write/update` rezultat v T03 |
| T07 | `DG.ZADEVA` | `ID_ZADEVA`, `DT_ZACETEK`, `SY_TISP` | `write/update` ← M08/M09/S01/A04 |
| T08 | `DG.DOKUMENT` | PDF; `ID_VRSTA_DOK=1341`, `ID_FORMAT=3`, `ID_STATUS=2` | `write` ← A05 |
| T09 | `DG.POT_ZADEVE` | faze 2/5/6/25, postopek 25, način 271, `SF_KONTROLA` | `write` ← A06 |
| T10 | `Q.SF.CM.LOAD.PDF.SIGN.IN` | PDF masovni zajem; ne ZIP | `message` ← A07 |
| T11 | Poročilo/e-pošta | ZIP, datum, tip, tabela, št. primerov; Excel polja | `message` ← M31/M32 |

## 9. SQL in procedure kartice

V L1 so še štiri manjše tehnične kartice, povezane s procesnimi vozlišči:

- **Q01 — SQL-01/02:** EP join proti `NP.CSD_DPP_PDF`, `SY_TISP <> 'B'`, naslednja neobdelana vloga, `FETCH FIRST ROW ONLY` → M04/M33.
- **Q02 — SQL-03:** aktivni `DG.IDENTIFIKATOR`, `ID_TIP_IDENT IN (1,9)`, dolžina 13 → M19.
- **Q03 — SQL-04/05:** pretekla obdelava in dvojnik drugega tipa → M25/M26.
- **Q04 — SQL-06/07:** `TP_OPOMBA + SF_DD_SKLEP_ODLOCBA` ter `DG.OSEBA.DT_SMRT` → M27/D01.
- **P01 — procedure:** osnovna, SD in AVT klica `DG.P_POISCI_ZADEVO`; vrnjeni `ID_ZADEVA` je prikazan na robu `call/return`.
- **P02 — procedure:** `DG.P_ZAKLJUCI_ZADEVO` z osmimi navedenimi parametri → A08/A03.
- **P03 — registracije:** `SS.EVIDENTIRANJE_VLOG` 86 (`014-47-1`/AVT), 87 (`PIZ`/UDG), 88 (`SD`/UDG), 89 (`AVT`/AVT); popolna preslikava klasifikacij je odprta.

## 10. Paketni zaključek in poročilo (L5)

- `M30` agregira vse zapise, vključno z napakami: `SF_REZULTAT NULL/1/2`, `TX_OPOMBA`, `DT_OBDELAVA`, `ID_ZADEVA`.
- `M31` izdela Excel z: `TX_DATOTEKA`, `SF_DD_SKLEP_ODLOCBA`, `SF_EMSO`, `SF_OSEBE`, `SF_ODLOCBA_BRANA`, `SF_REZULTAT`, `TX_OPOMBA`, `DT_SMRT`.
- `M32` pošlje e-pošto z nazivom ZIP, datumom prejema, vhodnim tipom, tabelo rezultatov in številom primerov. Prejemnik ni določen v viru in je označen kot odprto vprašanje.
- `M33` ponovno izvede SQL-02; DA vodi nazaj na M06, NE na M34.
- Statusna legenda mora biti vidna: `NULL = neobdelano`, `1 = uspešno`, `2 = obdelano z napako`; `DT_OBDELAVA` se zapiše za vsak končan PDF.

## 11. Odprta vprašanja in omejitve (vidno na platnu)

1. **Tip odločbe 4:** veja 7.d je določena, natančno pravilo prepoznave ni popolno — »preveriti v specifikaciji«.
2. **`TP_OPOMBA`:** potrjene kode 01/03/07/08; celoten šifrant ni podan — druge kombinacije so 7.g.
3. **`DG.POT_ZADEVE`:** vir navaja faze 2/5/6/25, popolna preslikava faz ni potrjena.
4. **E-pošta:** prejemnik ni določen.
5. **Pravica/UI:** konkretna implementacija pravice in uporabniškega vmesnika ni določena.
6. **Tehnični klici:** prikazujejo sled iz navodila, ne izvedbenega dokaza v workspace-u.

## 12. Containment, ID in robna pravila za XML

- Root celici `0` in `1`; vsi objekti imajo unikatne ID-je s prefiksi `lane_`, `m_`, `x_`, `r_`, `d_`, `a_`, `p_`, `t_`, `q_`, `edge_`.
- Vsi procesni objekti so otroci točno enega swimlane-a; robovi so otroci root `1`, ne naključno vozlišče.
- Noben rob ne sme imeti ročnih `Array` waypointov; uporablja se `mxGeometry` z `relative="1"` in `as="geometry"`, po potrebi `edgeStyle=orthogonalEdgeStyle`.
- Vsi robovi imajo obstoječe `source` in `target`, jasen label ter geometrijo. Povratna povezava M33→M06 se routa po zgornjem ali spodnjem robu, ne čez glavni tok.
- HTML oznake uporabljajo `html=1`; znaki `<`, `>`, `&` so XML-escaped.
- Odprta vprašanja so samostojne opombe s črtkano obrobo; ne smejo biti predstavljena kot procesna odločitev.

## 13. Sledljivost zahtev

| Zahteva | Pokritost v načrtu |
|---|---|
| REQ-008 | L2 vsebuje vhod, pravico, paketno zanko, 2.a–6.b, 7.a–7.g, izhode in poročanje; L3/L4 pokrivata SD, mrtve, AVT/PIZ; L5 pokriva nadaljevanje in konec. |
| REQ-009 | L1 vsebuje T01–T11, SQL-01–07, procedure, registracije, statuse in semantiko robov; odprta vprašanja so v L11. |
| REQ-010 | Ena stran, velika mreža, swimlane containment, barvna legenda, routing, unikatni ID-ji in XML pravila so določeni v L2/L3/L12. |

## 14. Izvedbeni kriteriji za STEP-011/012/013

- STEP-011 mora iz tega načrta izdelati eno `diagram` stran; nobene druge `diagram` strani ali zavihka.
- STEP-012 mora s parserjem potrditi vse M01–M34, X01–X04, R01–R06, D01/S01/S02/A01–A09/P01–P05, T01–T11, Q01–Q04 in procedure/registracije.
- STEP-012 mora potrditi vse oznake 2.a–7.g, napake, statuse `NULL/1/2`, `DT_OBDELAVA`, `DT_SMRT`, `ID_ZADEVA`, vse zahtevane objekte in semantike `read/write/update/call/message`.
- STEP-013 mora izvoziti enostranski diagram, pregledati celoto in povečave; brez rendererja mora ostati `BLOCKED/PARTIAL`, nikoli lažno `PASSED`.
