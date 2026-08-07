# NPDPSS001000 — inventar izvornih navodil

## 1. Identifikacija in obseg vira

- **Datoteka:** `NPDP - Navodila za programiranje - Shranjevanje CSD DPP v UDG NPDPSS001000.doc`
- **Format:** Microsoft Word OLE/Compound Document, Windows-1250.
- **Metapodatki iz `file`:** 18 strani, 4.073 besed, 23.222 znakov; naslov »Shranjevanje CSD Odločb o DPP iz BiZPIZ v UDG in CMOD (NPDPSS001000)«.
- **Različica/datum v dokumentu:** 1.0; 15. 06. 2026; osnovni dokument 19. 5. 2026.
- **Avtorji, navedeni v dokumentu:** Uroš Kovšca, Domen Dolar, Damjan Kobal, Ivana Grujić, Elizabeta Hribarček, Nataša Mrzlikar, Marjeta Kastelic, Darija Abramič.
- **Vključeno v obseg:** opis obdelave eVloge `014-47-1`, obvezne ZIP priloge, PDF odločb, kontrole, evidentiranje v UDG/eDosje, CMOD in e-poštno poročilo.
- **Izključeno iz obsega NPDPSS001000:** poglavja o prevzemu XLSX datoteke o postopkih CSD in poglavje o prevzemu XLSX seznama PDF odločb; dokument ju eksplicitno označi kot »ni del NPDPSS001000«.
- **Izključeno zaradi drugega projekta:** zaključni fragment »Shranjevanje izjav za Letni dodatek (NPLDSSEZ1000)« in Wordovi tehnični/stilski vnosi po njem.

## 2. Normalizirana struktura dokumenta

1. Povezava med programi.
2. Prevzem XLSX datoteke o postopkih CSD — **ni del NPDPSS001000**.
3. Prevzem XLSX datoteke o PDF odločbah — **ni del NPDPSS001000**.
4. Uvod/opis procesa DPP odločb iz CSD v UDG zadeve in CMOD.
5. Prejete datoteke in omejitve ZIP priloge.
6. Postopek s prejetimi datotekami.
7. Kontrole posamezne PDF odločbe, označene s koraki 2.a–7.g.
8. Končna obdelava paketa in preverjanje naslednje vloge.
9. Evidentiranje zadeve strokovnemu delavcu.
10. Evidentiranje primera v hrambo in avtomatično zapiranje zadeve.
11. Šifranti/registracije vlog za različne načine evidentiranja.
12. Uporabniški vmesnik za UDG, zapis dokumenta in poti zadeve.
13. CMOD masovni zajem, servisa `NPPZSS001000.insertPzIzbor` in `ZPIZCPR/setObvestiloWS`.

## 3. Akterji, sistemi in odgovornosti

| Element | Vloga v viru | Sledljivost |
|---|---|---|
| BiZPIZ / EP | Prejme eVlogo in ZIP; ZIP ostane v tabelah BiZPIZ, ne gre v delno evidentiranje GP. | `EP.VLOGE_ODDANE`, `EP.PRIPONKE_ODDANE` |
| Operativa | Ročno zažene obdelavo, ker so lahko tipi odločb še netestirani. | UI/izvajanje aplikacije |
| NPDPSS001000 | Preveri pravico, poišče novo vlogo, razpakira, bere PDF in vodi statuse. | aplikacijski proces |
| UDG/eDosje/DG | Ustvari zadeve, osebe, dokumente in poti zadeve. | `DG.*`, procedure |
| CMOD | Prejme PDF prek vrste za masovni zajem. ZIP se v CMOD ne pošilja neposredno. | `Q.SF.CM.LOAD.PDF.SIGN.IN` |
| CSD Ljubljana | Vir paketov upravnih aktov in podatkov/odločb. | eVloga, ZIP, naziv datoteke |
| Strokovni delavec | Ročno obdela neusklajene/neznane ali drugače izločene primere po razdelilniku. | vloga `014-47-1-SD` |
| E-pošta | Po koncu paketa pošlje rezultat in Excel prilogo. | prejemnik ni konkretiziran v viru |
| MOST | V viru nastopa pri ločenem prevzemu XLSX datotek, ki je izven NPDPSS001000. | izrecno out-of-scope |

## 4. Vhodni podatki in omejitve

- Vsaka eVloga `014-47-1` ima praviloma obvezno ZIP prilogo.
- Ime ZIP je sestavljeno iz tipa dokumentov, števila dokumentov in datuma `YYYY_MM_DD`, deli so ločeni z `_`; primer: `Sklep o ustavitvi postopka po ZUOPCSD - ni soglasja_98_2026_05_12.zip`.
- Dokumenti v ZIP so poimenovani z 13-mestnim EMŠO, na primer `1234567890123.PDF`.
- Ne-PDF priloge se ignorirajo.
- Omejitev priloge po protokolu je 50 MB, tehnično 60 MB.
- ZIP ostane v `EP.VLOGE_ODDANE`/`EP.PRIPONKE_ODDANE`; v CMOD se pošilja PDF ali XML, ne neposredno ZIP. Za dostop uporabnika do eVloge in ZIP je predviden nov UI za UDG.
- Tip odločbe v eVlogi je `SF_DD_SKLEP_ODLOCBA` z vrednostmi 1–6.

## 5. Glavni procesni inventar

### 5.1 Zagon in odkrivanje nove vloge

1. Uporabnik zažene obdelavo.
2. Sistem preveri uporabniško pravico `DPP_PDF_BJ`. Če pravice ni, se postopek takoj ustavi in izpiše, da uporabnik nima pravice.
3. Sistem primerja `ID_VLOGE_ODDANE` iz BiZPIZ s tabelo `NP.CSD_DPP_PDF`; upoštevajo se zapisi, kjer `SY_TISP <> 'B'`.
4. Če ni nove priloge, ni nove obdelave. Če obstaja vsaj ena neprenesena/neobdelana priloga, se obdelava nadaljuje za naslednjo vlogo/datoteko.
5. Za paket se avtomatsko evidentira osnovna eVloga `014-47-1` v eDosje CSDLJ s klasifikacijsko šifro 10390, stopnjo reševanja »splošno reševanje«, načinom »ostalo iz PIZ«, kratko vsebino »ostalo«, opombo »eVloga BiZPIZ« in začetkom `DT_PREJEMA`.
6. Za osnovno zadevo se pokliče `DG.P_POISCI_ZADEVO('DAVČNA ŠTEVILKA CSD LJUBLJANA', 'P', '014-47-1', NULL, NULL, NULL, NULL, NULL, GUID)`. Procedura vrne `ID_ZADEVA`.
7. `DG.ZADEVA.DT_ZACETEK` se posodobi na `DT_PREJEMA` (če `SY_TISP <> 'B'`).
8. ZIP se razpakira; vsaka PDF datoteka gre v obdelavo posamezne osebe.

### 5.2 Začetek posamezne PDF

9. Če je PDF pokvarjen/neberljiv, se zapiše `SF_REZULTAT`, `TX_OPOMBA = 'PDF ni berljiv'` in `DT_OBDELAVA` (timestamp); primer se zaključi z napako.
10. Ustvari/posodobi se zapis v `NP.CSD_DPP_PDF` z identiteto vloge, ZIP-a, datoteke, datumi, tipoma odločbe, EMŠO, `SF_OSEBE`, `ID_ZADEVA` in rezultatom.
11. Parser poišče prvo 13-mestno številko v besedilu odločbe; to je EMŠO osebe, za katero je odločba izdelana.

### 5.3 Kontrole EMŠO (koraki 2.a–2.d)

12. Prebrani EMŠO se shrani v `NP.CSD_DPP_PDF.SF_EMSO` (**2.a**).
13. Če EMŠO ni najden: `SF_EMSO = NULL`, napaka `EMŠO ni bil prebran`; ni naloge strokovnemu delavcu in ni avtomatičnega zapiranja; primer se zaključi (**2.b**).
14. Če prebrani EMŠO ni enak imenu datoteke (`SF_EMSO <> TX_DATOTEKA`): zapiše se `EMŠO ni enak`. Primer se evidentira strokovnemu delavcu za EMŠO iz dokumenta; pred evidentiranjem se poišče `SF_OSEBE` (**2.c**).
15. Če je EMŠO enak imenu datoteke (`SF_EMSO = TX_DATOTEKA`), se obdelava nadaljuje (**2.d**).

### 5.4 Iskanje osebe (koraki 3.a–3.d)

16. `SF_OSEBE` se poišče po aktivnem identifikatorju v `DG.IDENTIFIKATOR`: `ID_TIP_IDENT IN (1,9)`, `SF_IDENT = :SF_EMSO`, dolžina 13, `SF_AKTIVEN_IDENT = 'D'`, `SY_TISP <> 'B'`.
17. Če oseba ni najdena: `SF_OSEBE = NULL`, napaka `Oseba je neznana`; brez naloge in brez avtomatičnega zapiranja (**3.a**).
18. Če je najdenih več oseb: `SF_OSEBE = NULL`, napaka `Oseba ima neurejene identifikatorje`; brez naloge in brez avtomatičnega zapiranja (**3.b**).
19. Če je najden natanko en `SF_OSEBE`, se zapiše v `NP.CSD_DPP_PDF` in obdelava nadaljuje, če `SF_REZULTAT <> 2` (**3.c**).
20. Če je bila prej zaznana napaka `EMŠO ni enak`, se po uspešnem iskanju osebe takoj pripravi evidentiranje strokovnemu delavcu in obdelava te osebe konča (**3.d**).

### 5.5 Prepoznava tipa odločbe (koraki 4.a–4.d)

21. V vsebini PDF se poiščejo ključni stavki in določi `SF_ODLOCBA_BRANA`.
22. Mapiranje iz vira: `Sklep se ustavi` → 1; `Odločba se zavrne` → 2 (če je vhodni tip 2); dopolnitev trenutno ni določena; pozitivna odločba po ZUOPCSD → 5; odločba, kjer se ugotovi, da se je ... prevedel → 6; ostalo → neprepoznano. V dokumentu je pri nekaterih opisih besedilo zaradi starega OLE izpisa nepopolno, zato je to odprto vprašanje za analitika.
23. Prebrani tip se shrani v `NP.CSD_DPP_PDF.SF_ODLOCBA_BRANA` (**4.a**).
24. Če tip ni ugotovljen, se zapiše `SF_ODLOCBA_BRANA = 0`, napaka `Tip odločbe iz dokumenta ni znan`, primer gre strokovnemu delavcu (**4.b**).
25. Če se vhodni in prebrani tip razlikujeta, se zapiše `Tip odločbe ni enak prebranemu dokumentu`, primer gre strokovnemu delavcu (**4.c**).
26. Če sta tipa enaka, se nadaljuje (**4.d**).

### 5.6 Predhodne CSD obdelave in deduplikacija (koraki 5.a–6.b)

27. V `NP.CSD_DPP_OBDELAVA` se poišče EMŠO, pri čemer `SY_TISP <> 'B'`.
28. Če EMŠO ni v predhodnih obdelavah, se zapiše `Ni v predhodnjih obdelavah CSD`; primer gre strokovnemu delavcu (**5.a**).
29. Če je najden, se nadaljuje (**5.b**).
30. V `NP.CSD_DPP_PDF` se preveri, ali za isto osebo obstaja že uspešno obdelan zapis drugega tipa odločbe (`SF_REZULTAT <> 2`, isti `SF_OSEBE`, drugačen `SF_ODLOCBA_BRANA`).
31. Če obstaja tak zapis, se primer evidentira strokovnemu delavcu po razdelilniku in zapiše `Za to osebo smo že prej prejeli odločbo` (**6.a**).
32. Če različnega zapisa ni, se nadaljuje (**6.b**).
33. Za EMŠO, najden v `NP.CSD_DPP_OBDELAVA`, se glede na `TP_OPOMBA` kontrolira kombinacija z `SF_DD_SKLEP_ODLOCBA`; vir posebej navaja `TP_OPOMBA = 01` kot primer dvojnika z enim zapisom. Dodatne kombinacije so del odločitvene matrike 7.a–7.g.

### 5.7 Odločitvena matrika 7.a–7.g

| Veja | Pogoj | Izhod |
|---|---|---|
| 7.a | `DD_SKLEP_ODLOCBA = 1` in `TP_OPOMBA = 08` | Evidentiranje in avtomatičen zaključek v hrambo (`014-47-1-AVT`). |
| 7.b | `DD_SKLEP_ODLOCBA = 2` in `TP_OPOMBA IN (03,08)` | Evidentiranje in avtomatičen zaključek v hrambo. |
| 7.c | `DD_SKLEP_ODLOCBA = 3` in `TP_OPOMBA = 08` | Evidentiranje in avtomatičen zaključek v hrambo. |
| 7.d | `DD_SKLEP_ODLOCBA = 4` | Bazen `DO-PONOVNO IZPLAČILO PO MIROVANJU`, `014-47-1-PIZ`, `ID_SIGN_ZNAK` po registraciji; klasifikacija 10343, splošno reševanje, dolgotrajna oskrba. |
| 7.e | `DD_SKLEP_ODLOCBA = 5` in `TP_OPOMBA = 07` | Evidentiranje in avtomatičen zaključek v hrambo. |
| 7.f | `DD_SKLEP_ODLOCBA = 6` in `TP_OPOMBA = 07` | Evidentiranje in avtomatičen zaključek v hrambo. |
| 7.g | Vse druge kombinacije | Evidentiranje strokovnemu delavcu po razdelilniku (`014-47-1-SD`). |

## 6. Končni izhodi in paketna zanka

- Za vse primere brez napake se v `NP.CSD_DPP_PDF` zapišeta `SF_REZULTAT` in `ID_ZADEVA`; za vsak obdelan primer se zapiše `DT_OBDELAVA`.
- Po vseh primerih se izdela e-pošta s samodejnim obvestilom, nazivom ZIP-a, datumom prejema, vhodnim tipom in tabelo rezultatov (`SF_REZULTAT`: NULL = neobdelano, 1 = uspešno, 2 = z napako; `TX_OPOMBA`; število primerov).
- E-pošti se doda Excel rezultat za vse obdelane osebe s polji `TX_DATOTEKA`, `SF_DD_SKLEP_ODLOCBA`, `SF_EMSO`, `SF_OSEBE`, `SF_ODLOCBA_BRANA`, `SF_REZULTAT`, `TX_OPOMBA`, `DT_SMRT`.
- Nato se preveri naslednja neobdelana vloga/ZIP istega tipa z `EP.VLOGE_ODDANE` + `EP.PRIPONKE_ODDANE`, ki še nima `ID_VLOGE_ODDANE` v `NP.CSD_DPP_PDF`; če je število > 0, se paketna obdelava ponovi.

## 7. Evidentiranje strokovnemu delavcu in mrtvi primeri

1. Pred dodelitvijo se v `DG.OSEBA` poišče `DT_SMRT` za `SF_OSEBE` in shrani v `NP.CSD_DPP_PDF.DT_SMRT`.
2. Če `DT_SMRT` obstaja, je oseba mrtva: ne ustvari se naloga strokovnemu delavcu, ne glede na napako; izvede se avtomatično zapiranje zadeve.
3. Če `DT_SMRT` ne obstaja, se ustvari zadeva strokovnemu delavcu po razdelilniku: klasifikacija 10343, splošno reševanje, dolgotrajna oskrba, PDF upravnega akta z nazivom, datum začetka `DT_PREJEMA`; klic `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-SD',NULL,...,GUID)` in popravek `DT_ZACETEK`.

## 8. Avtomatična hramba in zaključek

- Zadeva se evidentira s klasifikacijo 10343, splošnim reševanjem in dolgotrajno oskrbo.
- PDF se umesti v zadevo in poimenuje z nazivom pred prvim `_` v `TX_ZIP`: `LEFT(TX_ZIP, CHARINDEX('_', TX_ZIP)-1)`.
- Faza PVI se ne opravi; zaključek je »rešitev brez akta«.
- Klic za vlogo `014-47-1-AVT`: `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-AVT',NULL,...,GUID)`.
- Zaključek: `DG.P_ZAKLJUCI_ZADEVO(ID_ZADEVA,3,15248,10,4676,NULL,NULL,NULL)`.

## 9. Podatkovni objekti in polja

### `NP.CSD_DPP_PDF`
`ID_CSD_PDF`, `ID_VLOGE_ODDANE`, `TX_REFERENCNA_OZNAKA`, `TX_ZIP`, `TX_DATOTEKA`, `DT_PREJEMA`, `SF_DD_SKLEP_ODLOCBA`, `DT_OBDELAVA`, `SF_EMSO`, `SF_OSEBE`, `SF_ODLOCBA_BRANA`, `ID_ZADEVA`, `SF_REZULTAT`, `TX_OPOMBA`, `DT_SMRT`.

### `NP.CSD_DPP_OBDELAVA`
Izhodna/pretekla tabela; uporabljena polja vključujejo `SF_EMSO`, `TP_OPOMBA`, `DT_SEZNAM`, `ST_SEZNAM`, `SY_TISP` in `SF_REZULTAT`. Vir vsebuje tudi izvoz: `SF_EMSO AS EMŠO`, `TX_UZIVALEC AS osebno_ime`, `DT_UST_DTDO AS datum`, `TX_OPOMBA AS opomba`, filtriranje `ST_SEZNAM = 5` in `SY_TISP <> 'B'`.

### EP in DG
- `EP.VLOGE_ODDANE`: `ID_VLOGE_ODDANE`, `SF_OSEBA`.
- `EP.PRIPONKE_ODDANE`: `ID_VLOGE_ODDANE`, vsebina ZIP, `SY_TISP`.
- `DG.IDENTIFIKATOR`: `ID_TIP_IDENT`, `SF_IDENT`, `SF_OSEBE`, `SF_AKTIVEN_IDENT`, `SY_TISP`.
- `DG.OSEBA`: `SF_OSEBE`, `DT_SMRT`, `SY_TISP`.
- `DG.ZADEVA`: `ID_ZADEVA`, `DT_ZACETEK`, `SY_TISP`.
- `DG.DOKUMENT`: PDF z `ID_VRSTA_DOK = 1341`.
- `DG.POT_ZADEVE`: faze, rešitve, postopki in način reševanja; vir navaja `ID_FAZA` 2, 5, 6 in 25, `ID_POSTOPEK = 25`, `ID_NACIN_RES = 271`, `SF_KONTROLA` 0/1 ter komentarje za skeniranje/dodane dokumente.

## 10. SQL, procedure in konfiguracija

- Preverjanje nove vloge: primerjava `EP` z `NP.CSD_DPP_PDF`, `SY_TISP <> 'B'`, `FETCH FIRST ROW ONLY`.
- Iskanje osebe: `DG.IDENTIFIKATOR`, aktivni identifikatorji tipa 1/9, dolžina 13.
- Pretekle obdelave: `NP.CSD_DPP_OBDELAVA`, prvi zapis po EMŠO.
- Deduplikacija: `NP.CSD_DPP_PDF`, uspešen zapis in drug tip odločbe.
- Naslednja vloga: `EP.VLOGE_ODDANE JOIN EP.PRIPONKE_ODDANE`, izločitev ID-jev, že prisotnih v `NP.CSD_DPP_PDF`.
- Osrednja procedura: `DG.P_POISCI_ZADEVO` s parametri identifikator, vrsta subjekta, vloga, IN/OUT `ID_ZADEVA`, XML, subjekt, status, akcija, GUID.
- Zaključna procedura: `DG.P_ZAKLJUCI_ZADEVO` z `IN_ID_ZADEVA`, `IN_ID_RESITEV`, `IN_ID_RESITEV_FAZA_POST`, `IN_ID_FAZA`, `IN_ID_SIGN_ZNAK`, `IN_KONTROLA`, `STATUS`, `OPIS`.
- Registracije `SS.EVIDENTIRANJE_VLOG`: ID 86 za `014-47-1`/AVT, ID 87 za `014-47-1-PIZ`/UDG, ID 88 za `014-47-1-SD`/UDG, ID 89 za `014-47-1-AVT`/AVT; klasifikacije/stopnje/načini so navedeni v izvornem SQL.
- Dokument: `DG.DOKUMENT_SEQ.NEXTVAL`, `ID_VRSTA_DOK = 1341`, `ID_FORMAT = 3`, `ID_STATUS = 2`, PDF ime v `TX_OPOMBE` in metapodatki prejema/skeniranja.
- Pot zadeve: dva eksplicitna INSERT-a v `DG.POT_ZADEVE`, med drugim faza 5 »Skeniranje vrnjenih dokumentov« in faza 2 »Dodani dokumenti«, postopek 25, način reševanja 271.
- CMOD: PDF gre v `Q.SF.CM.LOAD.PDF.SIGN.IN`; nato `NPPZSS001000.insertPzIzbor` in `ZPIZCPR/setObvestiloWS`.

## 11. Odprta vprašanja in tveganja za diagram

1. OLE ekstrakcija z `strings -el` je izgubila nekatere šumnike in dele besedila (npr. `odločba` je bila izpisana kot `odlo\nba`); v tem inventarju so očitne besede normalizirane, nejasni stavki pa so označeni.
2. Mapping za tip 4 in natančno besedilo pozitivne odločbe je v viru poškodovano/nepopolno; diagram mora prikazati »prepoznava tipa 4 — pravilo preveriti v specifikaciji« kot odprto vprašanje, ne pa izmišljene vsebine.
3. Vir uporablja tako `TP_OPOMBA` kot `TX_OPOMBA` in ne poda celotnega šifranta `TP_OPOMBA`; diagram mora ohraniti kode 01/03/07/08, druge kombinacije pa označiti kot »vse ostalo«.
4. Prejemniki e-pošte, natančna implementacija pravice in konkretni mehanizem UI niso določeni.
5. V viru je datum v primerku e-pošte `06.08.2018`, medtem ko je dokument posodobljen 2026; datum se obravnava kot primer vsebine, ne kot poslovno pravilo.

## 12. Kontrolna sled do izvornih odsekov

- Naslov/metapodatki in kazalo: začetek dokumenta.
- Vhod ZIP, omejitve in razlika ZIP/CMOD: odsek pred »Postopek s prejetimi datotekami«.
- Pravica, nova vloga, osnovna zadeva, razpakiranje: »Postopek s prejetimi datotekami«.
- EMŠO in oseba: koraki 2.a–3.d.
- Tip odločbe: koraki 4.a–4.d.
- Predhodne obdelave in podvojitve: koraki 5.a–6.b.
- Poslovne kombinacije: 7.a–7.g.
- Paketni zaključek/e-pošta/naslednja vloga: odsek pred »Evidentiranje zadeve strokovnemu delavcu«.
- Mrtvi primeri in dodelitev: »Evidentiranje zadeve strokovnemu delavcu«.
- Avtomatično zapiranje: »Evidentiranje primera v hrambo in avtomatično zapiranje zadeve«.
- Šifranti, dokument, pot, CMOD: zaključni tehnični odseki pred NPLDSSEZ1000.
