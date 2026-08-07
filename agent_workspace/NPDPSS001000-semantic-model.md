# NPDPSS001000 — semantični model procesnega toka

## Namen in sledljivost

Ta model je vmesni artefakt za izdelavo diagrama in ni diagram. Ločuje paketni tok od toka posamezne PDF odločbe ter ohranja konkretne pogoje, statuse, ciljne tabele, opombe napak in terminalne izhode iz `NPDPSS001000-source-inventory.md`.

**Legenda:** `P` = procesno vozlišče, `D` = odločitev, `D*` = odločitev z več kot dvema izhodoma, `T` = podatkovni zapis/posodobitev, `I` = integracijski klic, `E` = terminalni izhod.

## 1. Paketni tok — vozlišča

| ID | Tip | Vozlišče / dejanje | Podatki, status ali učinek |
|---|---|---|---|
| B01 | P | Operativa zažene obdelavo | Začetek izvajanja NPDPSS001000. |
| B02 | D | Preveri pravico `DPP_PDF_BJ` | Kontrola uporabniške pravice. |
| B03 | E | Ustavitev: pravica manjka | Izpiše se »uporabnik nima pravice«; paket se ne obdeluje. |
| B04 | D | Poišči novo vlogo/prilogo | Primerjava `EP.VLOGE_ODDANE` + `EP.PRIPONKE_ODDANE` z `NP.CSD_DPP_PDF`, ob upoštevanju `SY_TISP <> 'B'`. |
| B05 | E | Ni nove priloge | Ni nove obdelave; zagon se konča brez spremembe obdelave. |
| B06 | P | Izberi naslednjo eVlogo/ZIP | Izbere naslednjo nepreneseno/neobdelano vlogo/datoteko. |
| B07 | T | Evidentiraj osnovno vlogo | `014-47-1`, CSDLJ, klasifikacija `10390`, splošno reševanje, način `ostalo iz PIZ`, vsebina `ostalo`, opomba `eVloga BiZPIZ`, začetek `DT_PREJEMA`. |
| B08 | I | Poišči osnovno zadevo | `DG.P_POISCI_ZADEVO('DAVČNA ŠTEVILKA CSD LJUBLJANA','P','014-47-1',NULL,...,GUID)` → `ID_ZADEVA`. |
| B09 | T | Posodobi začetek zadeve | `DG.ZADEVA.DT_ZACETEK = DT_PREJEMA`, če `SY_TISP <> 'B'`. |
| B10 | P | Razpakiraj ZIP | ZIP ostane v EP; posamezne PDF datoteke se izločijo; ne-PDF priloge se ignorirajo. |
| B11 | D* | Ali je še PDF za obdelavo? | Iteracija po datotekah v izbranem ZIP-u. |
| B12 | P | Obdelaj eno PDF odločbo | Predaja v tok P01–P32. |
| B13 | P | Zaključi obdelavo paketa | Po vseh PDF primerih agregira rezultate. |
| B14 | P | Sestavi poročilo | E-pošta z nazivom ZIP, datumom prejema, vhodnim tipom, tabelo rezultatov in številom primerov. |
| B15 | P | Dodaj Excel rezultat | Polja: `TX_DATOTEKA`, `SF_DD_SKLEP_ODLOCBA`, `SF_EMSO`, `SF_OSEBE`, `SF_ODLOCBA_BRANA`, `SF_REZULTAT`, `TX_OPOMBA`, `DT_SMRT`. |
| B16 | D | Ali obstaja naslednja neobdelana vloga/ZIP? | EP join; izloči `ID_VLOGE_ODDANE`, že prisotne v `NP.CSD_DPP_PDF`. |
| B17 | E | Konec paketnega cikla | Po e-pošti in kadar B16 = NE. |

## 2. Tok posamezne PDF — vozlišča in stanje

| ID | Tip | Vozlišče / dejanje | Podatki, status ali učinek |
|---|---|---|---|
| P01 | D | Ali je PDF berljiv? | Preverjanje pokvarjene/neberljive datoteke. |
| P02 | T/E | Zapiši napako neberljivega PDF | `SF_REZULTAT = 2`, `TX_OPOMBA = 'PDF ni berljiv'`, `DT_OBDELAVA = timestamp`; brez nadaljnjih kontrol te datoteke. |
| P03 | T | Ustvari/posodobi zapis PDF | `NP.CSD_DPP_PDF`: identiteta vloge/ZIP/datoteke, datumi, vhodni tip, EMŠO, oseba, prebrani tip, zadeva, rezultat, opomba, smrt. |
| P04 | P | Preberi prvo 13-mestno številko | Parser iz besedila PDF določi kandidatni EMŠO. |
| P05 | T | Shrani prebrani EMŠO (2.a) | `SF_EMSO = prebrani EMŠO`. |
| P06 | D | Ali je EMŠO prebran? (2.b) | `SF_EMSO IS NULL` ali obstaja. |
| P07 | T/E | Napaka manjkajočega EMŠO | `SF_EMSO = NULL`; `TX_OPOMBA = 'EMŠO ni bil prebran'`; brez `014-47-1-SD` in brez avtomatskega zapiranja. |
| P08 | D | Ali EMŠO ustreza imenu datoteke? (2.c/2.d) | Primerjava `SF_EMSO` in `TX_DATOTEKA`. |
| P09 | P | Označi neusklajen EMŠO | `TX_OPOMBA = 'EMŠO ni enak'`; cilj je strokovni delavec, vendar je pred tem obvezno iskanje osebe. |
| P10 | P | Nadaljuj z ujemajočim EMŠO | Vhod v iskanje osebe. |
| P11 | P | Poišči osebo po aktivnem identifikatorju | `DG.IDENTIFIKATOR`: `ID_TIP_IDENT IN (1,9)`, dolžina 13, `SF_IDENT = SF_EMSO`, `SF_AKTIVEN_IDENT='D'`, `SY_TISP <> 'B'`. |
| P12 | D* | Rezultat iskanja osebe (3.a–3.c) | 0, več kot 1 ali natanko 1 zadetek. |
| P13 | T/E | Oseba neznana (3.a) | `SF_OSEBE = NULL`; `TX_OPOMBA = 'Oseba je neznana'`; brez naloge in brez avtomatskega zapiranja. |
| P14 | T/E | Neurejeni identifikatorji (3.b) | `SF_OSEBE = NULL`; `TX_OPOMBA = 'Oseba ima neurejene identifikatorje'`; brez naloge in brez avtomatskega zapiranja. |
| P15 | T | Shrani enolično osebo (3.c) | `SF_OSEBE = natanko en zadetek`; nadaljuj, če `SF_REZULTAT <> 2`. |
| P16 | D | Je bil EMŠO neusklajen? (3.d) | Prejšnja napaka `EMŠO ni enak` po uspešnem iskanju osebe. |
| P17 | P | Pripravi strokovno obravnavo za EMŠO iz dokumenta | Primer se konča v veji SD; pred dodelitvijo se še preveri smrt (O01–O04). |
| P18 | P | Prepoznaj tip odločbe | Iskanje ključnih stavkov; določi `SF_ODLOCBA_BRANA`. Tip 4 je odprto vprašanje v viru. |
| P19 | T | Shrani prebrani tip (4.a) | `NP.CSD_DPP_PDF.SF_ODLOCBA_BRANA`. |
| P20 | D | Ali je tip prepoznan? (4.b) | Če ni: vrednost `0`. |
| P21 | T/E | Tip ni znan | `SF_ODLOCBA_BRANA = 0`; `TX_OPOMBA = 'Tip odločbe iz dokumenta ni znan'`; strokovni delavec po veji smrtne kontrole. |
| P22 | D | Ali vhodni in prebrani tip ustrezata? (4.c/4.d) | Primerjava `SF_DD_SKLEP_ODLOCBA` in `SF_ODLOCBA_BRANA`. |
| P23 | T/E | Tip ni enak prebranemu dokumentu | `TX_OPOMBA = 'Tip odločbe ni enak prebranemu dokumentu'`; strokovni delavec po veji smrtne kontrole. |
| P24 | P | Nadaljuj s predhodnimi CSD obdelavami | Vhod v `NP.CSD_DPP_OBDELAVA`. |
| P25 | D | Ali EMŠO obstaja v predhodnih obdelavah? (5.a/5.b) | Iskanje ob `SY_TISP <> 'B'`. |
| P26 | T/E | Ni v predhodnih obdelavah | `TX_OPOMBA = 'Ni v predhodnjih obdelavah CSD'`; strokovni delavec po veji smrtne kontrole. |
| P27 | P | Preberi predhodno obdelavo | Uporabi `TP_OPOMBA`, `DD_SKLEP_ODLOCBA`, `SF_REZULTAT` in druge podatke. |
| P28 | D | Ali že obstaja uspešna odločba drugega tipa? (6.a/6.b) | `NP.CSD_DPP_PDF`: isti `SF_OSEBE`, drug `SF_ODLOCBA_BRANA`, `SF_REZULTAT <> 2`. |
| P29 | T/E | Predhodna odločba drugega tipa | `TX_OPOMBA = 'Za to osebo smo že prej prejeli odločbo'`; strokovni delavec po veji smrtne kontrole. |
| P30 | D* | Matrika kombinacije 7.a–7.g | Primerjava `DD_SKLEP_ODLOCBA` in `TP_OPOMBA`. |
| P31 | P | Avtomatska hramba/zaključek (7.a, 7.b, 7.c, 7.e, 7.f) | Vhod v O05–O10; `014-47-1-AVT`. |
| P32 | P | PIZ bazen (7.d) | `DO-PONOVNO IZPLAČILO PO MIROVANJU`, `014-47-1-PIZ`, `ID_SIGN_ZNAK` po registraciji, klasifikacija `10343`, dolgotrajna oskrba; nato evidentiranje po PIZ poti. |
| P33 | P | Strokovni delavec (7.g) | Vhod v O01–O04; `014-47-1-SD`, razdelilnik. |

## 2.a Terminalna vozlišča kot grafični cilji

| ID | Tip | Vozlišče | Povezava/učinek |
|---|---|---|---|
| O01 | E | Mrtva oseba — avtomatsko zapiranje | `DT_SMRT` obstaja; brez naloge SD. |
| O02 | P | Živa oseba — ustvari SD zadevo | `DT_SMRT` ne obstaja; dodelitev po razdelilniku. |
| O03 | T | Zapiši SD rezultat in zadevo | `ID_ZADEVA`, rezultat/opomba in `DT_OBDELAVA`. |
| O04 | E | Vrnitev iz SD veje | Nadaljuje na `B11`. |
| O05 | P | Ustvari AVT zadevo | Vloga `014-47-1-AVT`. |
| O06 | T | Vstavi PDF dokument | `DG.DOKUMENT`, `ID_VRSTA_DOK=1341`. |
| O07 | T | Vstavi pot zadeve | `DG.POT_ZADEVE`, brez PVI. |
| O08 | I | Zaključi AVT zadevo | `DG.P_ZAKLJUCI_ZADEVO(...)`. |
| O09 | P | Evidentiraj PIZ bazen | `014-47-1-PIZ`, `DO-PONOVNO IZPLAČILO PO MIROVANJU`. |
| O10 | T | Zapiši uspešen rezultat | `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA`; na `B11`. |

## 3. Robovi glavnega in PDF toka

| Edge ID | Od → Do | Pogoj/oznaka |
|---|---|---|
| BE01 | B01 → B02 | zagon |
| BE02 | B02 → B03 | NE: pravice ni |
| BE03 | B02 → B04 | DA: `DPP_PDF_BJ` |
| BE04 | B04 → B05 | NE: ni nove priloge |
| BE05 | B04 → B06 | DA: obstaja neobdelana |
| BE06 | B06 → B07 → B08 → B09 → B10 | inicializacija paketa |
| BE07 | B10 → B11 | datoteke ZIP |
| BE08 | B11 → B12 | DA: naslednja PDF |
| BE09 | B11 → B13 | NE: vse PDF obdelane |
| BE10 | B12 → B13 | po končanem primeru; `NP.CSD_DPP_PDF` posodobljen |
| BE11 | B13 → B14 → B15 → B16 | paketni rezultat in e-pošta |
| BE12 | B16 → B06 | DA: naslednja vloga/ZIP |
| BE13 | B16 → B17 | NE: konec |
| PE01 | P01 → P02 | NE: PDF neberljiv |
| PE02 | P01 → P03 | DA: PDF berljiv |
| PE03 | P03 → P04 → P05 → P06 | parser/EMŠO |
| PE04 | P06 → P07 | NE: EMŠO manjka |
| PE05 | P06 → P08 | DA: EMŠO obstaja |
| PE06 | P08 → P09 | NE: `SF_EMSO <> TX_DATOTEKA` |
| PE07 | P08 → P10 | DA: enaka |
| PE08 | P09 → P11 | obvezno iskanje osebe |
| PE09 | P10 → P11 | normalna pot |
| PE10 | P11 → P12 | rezultat iskanja |
| PE11 | P12 → P13 | 0 zadetkov |
| PE12 | P12 → P14 | >1 zadetek |
| PE13 | P12 → P15 | 1 zadetek |
| PE14 | P15 → P16 | oseba shranjena |
| PE15 | P16 → P17 | DA: neusklajen EMŠO |
| PE16 | P16 → P18 | NE: ujemanje |
| PE17 | P17 → O01 | priprava SD; preveri smrt |
| PE18 | P18 → P19 → P20 | prepoznava tipa |
| PE19 | P20 → P21 | NE: tip ni znan |
| PE20 | P20 → P22 | DA: tip znan |
| PE21 | P22 → P23 | NE: tipa se razlikujeta |
| PE22 | P22 → P24 | DA: tipa enaka |
| PE23 | P24 → P25 | kontrola predhodnih obdelav |
| PE24 | P25 → P26 | NE: EMŠO ni najden |
| PE25 | P25 → P27 | DA: najden |
| PE26 | P27 → P28 | deduplikacija |
| PE27 | P28 → P29 | DA: druga uspešna odločba |
| PE28 | P28 → P30 | NE: ni dvojnika |
| PE29 | P30 → P31 | 7.a/7.b/7.c/7.e/7.f |
| PE30 | P30 → P32 | 7.d |
| PE31 | P30 → P33 | 7.g/vse drugo |
| PE32 | P02 → B11 | primer zaključen, naslednja PDF |
| PE33 | P07/P13/P14/P21/P23/P26/P29 → B11 | terminalni primer; paketna zanka |
| PE34 | P31/P32/P33 → B11 | izhod posamezne obdelave |

## 4. Terminalni izhodi in izhodna pravila

### O01–O04 — strokovni delavec, z obvezno kontrolo smrti

1. Poišči `DG.OSEBA.DT_SMRT` za `SF_OSEBE` in shrani `NP.CSD_DPP_PDF.DT_SMRT`.
2. **O01 — mrtva oseba:** `DT_SMRT` obstaja → ne ustvari naloge SD, avtomatično zapri zadevo; velja ne glede na predhodno napako.
3. **O02 — živa oseba:** `DT_SMRT` ne obstaja → ustvari zadevo po razdelilniku: klasifikacija `10343`, splošno reševanje, dolgotrajna oskrba, PDF upravnega akta; `014-47-1-SD`; popravi `DG.ZADEVA.DT_ZACETEK = DT_PREJEMA`.
4. **O03 — tehnični zapis SD:** evidentiraj `ID_ZADEVA`, dokument in rezultat/opombo v `NP.CSD_DPP_PDF`.
5. **O04 — vrnitev v paket:** po O01 ali O02/O03 zapiši `DT_OBDELAVA` in nadaljuj na `B11`.

### O05–O10 — avtomatska hramba in PIZ

- **O05 — AVT zadeva:** klasifikacija `10343`, splošno reševanje, dolgotrajna oskrba; vloga `014-47-1-AVT`.
- **O06 — dokument v zadevi:** PDF, `ID_VRSTA_DOK = 1341`, `ID_FORMAT = 3`, `ID_STATUS = 2`; naziv = del `TX_ZIP` pred prvim `_`.
- **O07 — pot zadeve:** INSERT v `DG.POT_ZADEVE`; faza/postopek po tehnični specifikaciji, brez PVI; rešitev »rešitev brez akta«.
- **O08 — avtomatski zaključek:** `DG.P_ZAKLJUCI_ZADEVO(ID_ZADEVA,3,15248,10,4676,NULL,NULL,NULL)`.
- **O09 — PIZ bazen:** `DO-PONOVNO IZPLAČILO PO MIROVANJU`, vloga `014-47-1-PIZ`, registracijski `ID_SIGN_ZNAK`; nato UDG/PIZ evidentiranje.
- **O10 — zapiši uspeh:** `SF_REZULTAT = 1`, `ID_ZADEVA`, `DT_OBDELAVA`; vrnitev na `B11`.

## 5. Matrika 7.a–7.g

| Veja | Natančen pogoj | Tok | Status/izhodi |
|---|---|---|---|
| 7.a | `DD_SKLEP_ODLOCBA=1 AND TP_OPOMBA=08` | O05–O10 | avtomatska hramba + zaključek |
| 7.b | `DD_SKLEP_ODLOCBA=2 AND TP_OPOMBA IN (03,08)` | O05–O10 | avtomatska hramba + zaključek |
| 7.c | `DD_SKLEP_ODLOCBA=3 AND TP_OPOMBA=08` | O05–O10 | avtomatska hramba + zaključek |
| 7.d | `DD_SKLEP_ODLOCBA=4` | O09 | PIZ bazen; odprto: natančno pravilo tipa 4 |
| 7.e | `DD_SKLEP_ODLOCBA=5 AND TP_OPOMBA=07` | O05–O10 | avtomatska hramba + zaključek |
| 7.f | `DD_SKLEP_ODLOCBA=6 AND TP_OPOMBA=07` | O05–O10 | avtomatska hramba + zaključek |
| 7.g | vse druge kombinacije | O01–O04 | strokovni delavec po razdelilniku |

## 6. Statusne spremembe

| Trenutek | Tabela/polje | Vrednost/pravilo |
|---|---|---|
| Napaka PDF ali poslovna kontrola | `NP.CSD_DPP_PDF.SF_REZULTAT` | `2` = obdelano z napako; `TX_OPOMBA` dobesedno po veji. |
| Uspešna obdelava | `NP.CSD_DPP_PDF.SF_REZULTAT` | `1` = uspešno obdelano. |
| Pred obdelavo | `SF_REZULTAT` | `NULL` = neobdelano; uporabljeno pri iskanju naslednjih vlog. |
| Vsak končan primer | `DT_OBDELAVA` | timestamp ob zaključku primera. |
| Identiteta | `SF_EMSO`, `SF_OSEBE`, `SF_ODLOCBA_BRANA` | zapisani po uspešnih kontrolah oziroma `NULL/0` pri ustreznih napakah. |
| Smrt | `DT_SMRT` | vrednost iz `DG.OSEBA`; vpliva na preskok dodelitve SD. |
| Zadeva | `ID_ZADEVA` | zapisana po evidentiranju v UDG/DG. |

## 7. Terminalna sledljivost

- Vsak terminalni PDF izhod (P02, P07, P13, P14, P21, P23, P26, P29, O01, O02/O03, O05–O09) ima zapis rezultata/opombe ali zadeve, nato `DT_OBDELAVA` in povezavo v paketno zanko `B11`.
- Edini terminalni izhod celotnega zagona je B03, B05 ali B17; B03 in B05 se končata pred obdelavo paketa, B17 po poročanju.
- Nobena napaka, razen manjkajoče pravice ali neobstoja nove priloge, ne ustavi celotne paketne zanke; napaka se zabeleži na posameznem PDF in obdelava nadaljuje z naslednjo datoteko.
- Ne-PDF priloge niso napaka; ignorirajo se pri razpakiranju.

## 8. Odprta vprašanja, ki morajo biti v diagramu označena

1. Natančno besedilo in mapiranje prepoznave tipa odločbe 4 ni popolno v izvoru; diagram uporabi oznako »pravilo preveriti v specifikaciji«.
2. Celoten šifrant `TP_OPOMBA` ni naveden; eksplicitne kode 01/03/07/08 ostanejo, druge kombinacije gredo v 7.g.
3. Prejemnik e-pošte in konkretna implementacija pravice/UI nista določena.
4. Vir navaja faze `2`, `5`, `6` in `25` v tehničnem opisu `DG.POT_ZADEVE`; končni diagram mora pri posameznem INSERT-u ohraniti virno sled in ne ugibati manjkajoče preslikave.
