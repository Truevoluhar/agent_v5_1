# NPDPSS001000 — odločitvena matrika končnih izhodov

## Namen in sledljivost

Ta artefakt operacionalizira korake 7.a–7.g ter razdelka o evidentiranju strokovnemu delavcu, mrtvih osebah, avtomatski hrambi in zaključevanju zadeve. Temelji na `NPDPSS001000-semantic-model.md` (vozlišča `P21`, `P23`, `P26`, `P29`, `P30–P33`, `O01–O10`) in `NPDPSS001000-source-inventory.md` (odseki o izhodnih vejah). Ne uvaja novih poslovnih pravil.

## 1. Prioritetni algoritem izhoda

Za vsako PDF datoteko se uporablja naslednje zaporedje:

1. Posodobi zapis `NP.CSD_DPP_PDF` in pri poslovni/tehnični napaki nastavi `SF_REZULTAT = 2`, ustrezno `TX_OPOMBA` ter `DT_OBDELAVA`.
2. Če je znan `SF_OSEBE` in izhod vodi v strokovno obravnavo ali v viru določeno izločeno vejo, preberi `DG.OSEBA.DT_SMRT` in vrednost shrani v `NP.CSD_DPP_PDF.DT_SMRT`.
3. **Če `DT_SMRT` obstaja, ima mrtvi primer prednost:** ne ustvari naloge `014-47-1-SD`; zadevo je treba avtomatsko zapreti, ne glede na predhodno napako.
4. Če `DT_SMRT` ne obstaja, se izhod, ki zahteva ročno obravnavo, evidentira kot `014-47-1-SD` in dodeli po razdelilniku.
5. Pri uspešni avtomatski hrambi/PIZ poti se zapiše `SF_REZULTAT = 1`, `ID_ZADEVA` in `DT_OBDELAVA`; nato se primer vrne v paketno zanko.

> **Virno pravilo:** `DT_SMRT` je izrecno kontroliran pred dodelitvijo strokovnemu delavcu. Vir določa avtomatsko zapiranje mrtvega primera »ne glede na napako«; zato matrika loči predhodni rezultat/opombo od končnega dejanja.

## 2. Matrika poslovnih kombinacij 7.a–7.g

| Oznaka | Pogoj (`DD_SKLEP_ODLOCBA`, `TP_OPOMBA`) | Ciljni izhod | Vloga | Klasifikacija / postopek | Končni rezultat |
|---|---|---|---|---|---|
| 7.a | `1 AND 08` | Avtomatska hramba | `014-47-1-AVT` | `10343`, splošno reševanje, dolgotrajna oskrba | O05–O08; `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA` |
| 7.b | `2 AND (03 OR 08)` | Avtomatska hramba | `014-47-1-AVT` | enako kot 7.a | O05–O08; `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA` |
| 7.c | `3 AND 08` | Avtomatska hramba | `014-47-1-AVT` | enako kot 7.a | O05–O08; `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA` |
| 7.d | `4` | PIZ bazen | `014-47-1-PIZ` | `DO-PONOVNO IZPLAČILO PO MIROVANJU`; `ID_SIGN_ZNAK` po registraciji; `10343`, splošno reševanje, dolgotrajna oskrba | O09; po PIZ evidentiranju `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA` |
| 7.e | `5 AND 07` | Avtomatska hramba | `014-47-1-AVT` | enako kot 7.a | O05–O08; `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA` |
| 7.f | `6 AND 07` | Avtomatska hramba | `014-47-1-AVT` | enako kot 7.a | O05–O08; `SF_REZULTAT=1`, `ID_ZADEVA`, `DT_OBDELAVA` |
| 7.g | Vse druge kombinacije | Strokovni delavec | `014-47-1-SD` | `10343`, splošno reševanje, dolgotrajna oskrba; dodelitev po razdelilniku | O01–O04; živa oseba dobi SD zadevo, nato `DT_OBDELAVA` |

**Odprto vprašanje:** za tip odločbe `4` vir določa vejo 7.d, vendar ne podaja popolnega pravila prepoznave tipa/kombinacije; diagram mora to označiti kot »pravilo preveriti v specifikaciji«.

## 3. Matrika izločenih/napaknih primerov

| Sprožilec | Koda/oznaka | `SF_REZULTAT` | `TX_OPOMBA` | `SF_OSEBE` / naslednje dejanje | Ali gre na DT_SMRT? |
|---|---|---:|---|---|---|
| PDF ni berljiv | P01 → P02 | 2 | `PDF ni berljiv` | Primer se zaključi; naslednja PDF | Ne, oseba ni zanesljivo znana |
| EMŠO ni prebran | 2.b / P06 → P07 | 2 | `EMŠO ni bil prebran` | `SF_EMSO=NULL`; brez SD in brez avtomatskega zapiranja; naslednja PDF | Ne |
| EMŠO ni enak imenu datoteke | 2.c/2.d | napaka se zapiše | `EMŠO ni enak` | Osebo je še vedno treba poiskati po EMŠO iz dokumenta; nato SD-veja | Da, če je `SF_OSEBE` najden |
| Oseba ni najdena | 3.a | 2 | `Oseba je neznana` | `SF_OSEBE=NULL`; brez naloge in brez avtomatskega zapiranja; naslednja PDF | Ne |
| Več zadetkov osebe | 3.b | 2 | `Oseba ima neurejene identifikatorje` | `SF_OSEBE=NULL`; brez naloge in brez avtomatskega zapiranja; naslednja PDF | Ne |
| Tip odločbe ni prepoznan | 4.b | 2 | `Tip odločbe iz dokumenta ni znan` | `SF_ODLOCBA_BRANA=0`; izhod v SD-vejo | Da, če je `SF_OSEBE` znan |
| Tip se ne ujema | 4.c/4.d | 2 | `Tip odločbe ni enak prebranemu dokumentu` | Izhod v SD-vejo | Da, če je `SF_OSEBE` znan |
| EMŠO ni v predhodnih obdelavah CSD | 5.a | 2 | `Ni v predhodnjih obdelavah CSD` | Izhod v SD-vejo | Da, če je `SF_OSEBE` znan |
| Predhodna uspešna odločba drugega tipa | 6.a/6.b | 2 | `Za to osebo smo že prej prejeli odločbo` | Izhod v SD-vejo | Da, če je `SF_OSEBE` znan |

Pri napakah, pri katerih vir ne podaja eksplicitne številčne kode, se ne domneva dodatna koda; zabeleži se virna opomba in čas `DT_OBDELAVA`.

## 4. Podmatrika strokovnega delavca in mrtvih oseb

| Vhod | Kontrola | Veja | Dejanje | Vloga / klic | Zapis |
|---|---|---|---|---|---|
| 7.g ali napaka z znanim `SF_OSEBE` | Poišči `DG.OSEBA.DT_SMRT` za `SF_OSEBE` | `DT_SMRT` obstaja | Mrtva oseba: ne ustvari SD naloge; avtomatsko zapiranje | Brez `014-47-1-SD`; uporabi AVT zaključek `DG.P_ZAKLJUCI_ZADEVO` | `DT_SMRT` se shrani v PDF zapis; ohrani se predhodni `SF_REZULTAT`/`TX_OPOMBA`; nato `DT_OBDELAVA` |
| 7.g ali napaka z znanim `SF_OSEBE` | Ista kontrola | `DT_SMRT` ne obstaja | Ustvari/dodeli zadevo po razdelilniku | `014-47-1-SD`; `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-SD',NULL,...,GUID)` | `ID_ZADEVA`, rezultat/opomba, popravek `DG.ZADEVA.DT_ZACETEK=DT_PREJEMA`, `DT_OBDELAVA` |
| Napaka brez `SF_OSEBE` | Kontrola ni izvedljiva | `SF_OSEBE=NULL` | Brez SD naloge in brez avtomatskega zaključevanja; primer ostane napaka | Noben klic za SD | `SF_REZULTAT=2`, virna `TX_OPOMBA`, `DT_OBDELAVA` |

**Pomembna razlika:** »mrtvi primer« je izhodna veja za znano osebo in preskoči SD dodelitev. »Neznana oseba« oziroma »neurejeni identifikatorji« nista mrtva primera in ne smeta biti narisana kot avtomatsko zapiranje.

## 5. Podmatrika avtomatske hrambe, PIZ in zaključka

| Izhod | Ustvari zadevo | Dokument | Pot zadeve | Zaključek / integracija |
|---|---|---|---|---|
| Avtomatska hramba (7.a/b/c/e/f) | `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-AVT',NULL,...,GUID)` → `ID_ZADEVA` | `DG.DOKUMENT`: PDF; `ID_VRSTA_DOK=1341`, `ID_FORMAT=3`, `ID_STATUS=2`; naziv = del `TX_ZIP` pred prvim `_` | INSERT v `DG.POT_ZADEVE`, brez PVI; faza/postopek po tehnični specifikaciji; rešitev »rešitev brez akta« | `DG.P_ZAKLJUCI_ZADEVO(ID_ZADEVA,3,15248,10,4676,NULL,NULL,NULL)`; rezultat `1` |
| PIZ bazen (7.d) | Registracija za `014-47-1-PIZ`; `ID_SIGN_ZNAK` po registraciji | PIZ/UDG evidentiranje po virni PIZ poti | Bazen `DO-PONOVNO IZPLAČILO PO MIROVANJU` | Rezultat `1`, `ID_ZADEVA`, `DT_OBDELAVA`; podrobno CMOD/UDG dejanje je na tehnični strani |
| Mrtva oseba | Uporabi avtomatsko/AVT zapiranje; brez SD | Kot zahteva virna hramba | Kot pri avtomatskem izhodu | Klic `DG.P_ZAKLJUCI_ZADEVO`; predhodna napaka/opomba ostane zapisana |

## 6. Statusna pogodba

| Trenutek | Polje | Zahtevana vrednost |
|---|---|---|
| Neobdelan zapis | `SF_REZULTAT` | `NULL` |
| Tehnična ali poslovna napaka | `SF_REZULTAT` | `2` |
| Uspešno evidentiran/zaključen primer | `SF_REZULTAT` | `1` |
| Vsak končan PDF primer | `DT_OBDELAVA` | timestamp, tudi pri napaki |
| Znana oseba | `SF_OSEBE` | natanko en zadetek iz `DG.IDENTIFIKATOR`/`DG.OSEBA` |
| Mrtva oseba | `DT_SMRT` | vrednost iz `DG.OSEBA`; vpliva na preskok SD |
| Evidentirana zadeva | `ID_ZADEVA` | ID vrnjene/ustvarjene zadeve, kadar izhod ustvari zadevo |

## 7. Validacijska sled

- Vse vrstice 7.a–7.g so enolično preslikane v `P30` in `PE29–PE31` semantičnega modela.
- Vsi izhodi se zaključijo v `O01–O10` ali napakah `P02/P07/P13/P14/P21/P23/P26/P29`, nato v paketni zanki `B11`.
- `DT_SMRT` je eksplicitno preverjen samo tam, kjer je `SF_OSEBE` znan; neznana oseba nima dovolj podatkov za kontrolo smrti.
- `DG.P_ZAKLJUCI_ZADEVO` je naveden pri AVT/mrtvem izhodu z vsemi parametri, ki jih vir eksplicitno poda.
