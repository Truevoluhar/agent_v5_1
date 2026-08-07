# NPDPSS001000 — tehnični inventar podatkov, SQL kontrol, procedur in integracij

## Namen in meje

Ta artefakt je tehnična sledljivost za STEP-005 in je namenjen neposredni uporabi pri izdelavi strani 01, 05 in 06 draw.io diagrama. Temelji na `NPDPSS001000-source-inventory.md`, `NPDPSS001000-semantic-model.md`, `NPDPSS001000-outcome-decision-matrix.md` in `NPDPSS001000-layout-plan.md`. Ne implementira in ne izvaja SQL, UDG, CMOD ali spletnih servisov; prikazuje le virno navedene podatke, kontrole in klice.

Nejasnosti niso dopolnjene z domnevami. Tip odločbe 4, celoten šifrant `TP_OPOMBA`, natančno mapiranje faz `DG.POT_ZADEVE` in prejemnik e-pošte ostanejo označeni kot odprta vprašanja.

## 1. Podatkovni objekti in ključna polja

| ID | Objekt | Ključna polja / vsebina | Namen v toku | Operacije / sled |
|---|---|---|---|---|
| T-01 | `EP.VLOGE_ODDANE` | `ID_VLOGE_ODDANE`, `SF_OSEBA` | vhodna eVloga `014-47-1` in iskanje naslednje vloge | `read`; v kombinaciji s `EP.PRIPONKE_ODDANE` |
| T-02 | `EP.PRIPONKE_ODDANE` | `ID_VLOGE_ODDANE`, vsebina ZIP, `SY_TISP` | obvezna ZIP priloga; ZIP ostane v EP | `read`; izločanje `SY_TISP = 'B'` |
| T-03 | `NP.CSD_DPP_PDF` | `ID_CSD_PDF`, `ID_VLOGE_ODDANE`, `TX_REFERENCNA_OZNAKA`, `TX_ZIP`, `TX_DATOTEKA`, `DT_PREJEMA`, `SF_DD_SKLEP_ODLOCBA`, `DT_OBDELAVA`, `SF_EMSO`, `SF_OSEBE`, `SF_ODLOCBA_BRANA`, `ID_ZADEVA`, `SF_REZULTAT`, `TX_OPOMBA`, `DT_SMRT` | delovni zapis ene PDF odločbe, deduplikacija in rezultat | `read/write/update`; `SF_REZULTAT NULL/1/2` |
| T-04 | `NP.CSD_DPP_OBDELAVA` | `SF_EMSO`, `TP_OPOMBA`, `DT_SEZNAM`, `ST_SEZNAM`, `SY_TISP`, `SF_REZULTAT`; izvoz vključuje `TX_UZIVALEC`, `DT_UST_DTDO`, `TX_OPOMBA` | pretekle CSD obdelave in kombinacije odločbe/opombe | `read`; filter `ST_SEZNAM = 5`, `SY_TISP <> 'B'` |
| T-05 | `DG.IDENTIFIKATOR` | `ID_TIP_IDENT`, `SF_IDENT`, `SF_OSEBE`, `SF_AKTIVEN_IDENT`, `SY_TISP` | preslikava EMŠO → natanko ena oseba | `read`; aktivni identifikatorji tipa 1/9 |
| T-06 | `DG.OSEBA` | `SF_OSEBE`, `DT_SMRT`, `SY_TISP` | kontrola smrti pred SD dodelitvijo | `read`; rezultat se zapiše v `NP.CSD_DPP_PDF.DT_SMRT` |
| T-07 | `DG.ZADEVA` | `ID_ZADEVA`, `DT_ZACETEK`, `SY_TISP` | osnovna, SD ali AVT/PIZ zadeva | `read/update`; `DT_ZACETEK := DT_PREJEMA` v virno navedenih poteh |
| T-08 | `DG.DOKUMENT` | `DG.DOKUMENT_SEQ.NEXTVAL`, `ID_VRSTA_DOK=1341`, `ID_FORMAT=3`, `ID_STATUS=2`, PDF ime/metapodatki v `TX_OPOMBE` | evidentiranje PDF v UDG/eDosje | `write`; PDF, ne neposredni ZIP |
| T-09 | `DG.POT_ZADEVE` | `ID_FAZA`, `ID_POSTOPEK=25`, `ID_NACIN_RES=271`, `SF_KONTROLA` 0/1, komentarji | pot zadeve in tehnična dejanja dokumenta | `write`; vir navaja faze 2, 5, 6, 25; popolno mapiranje je odprto |
| T-10 | CMOD queue `Q.SF.CM.LOAD.PDF.SIGN.IN` | PDF sporočilo za masovni zajem | prenos PDF iz UDG/NP toka v CMOD | `message`; ZIP se ne pošilja neposredno |
| T-11 | e-poštno poročilo | naziv ZIP, datum prejema, vhodni tip, tabela rezultatov, število primerov | poročanje po zaključku paketa | `message`; prejemnik ni določen v viru |

## 2. SQL kontrole in predikati

| ID | Kontrola | Virna logika / predikat | Vhod → izhod |
|---|---|---|---|
| SQL-01 | Nova vloga/priloga | `EP.VLOGE_ODDANE` + `EP.PRIPONKE_ODDANE`; primerjava `ID_VLOGE_ODDANE` z `NP.CSD_DPP_PDF`; `SY_TISP <> 'B'`; vir omenja `FETCH FIRST ROW ONLY` | EP → izbrana neobdelana vloga/ZIP ali veja »ni nove priloge« |
| SQL-02 | Neobdelana naslednja vloga | join EP tabel in izločitev ID-jev, že prisotnih v `NP.CSD_DPP_PDF` | paketna zanka → naslednja vloga ali konec |
| SQL-03 | Iskanje osebe po EMŠO | `DG.IDENTIFIKATOR`: `ID_TIP_IDENT IN (1,9)`, `SF_IDENT = :SF_EMSO`, dolžina 13, `SF_AKTIVEN_IDENT = 'D'`, `SY_TISP <> 'B'` | EMŠO → 0, več ali natanko 1 `SF_OSEBE` |
| SQL-04 | Predhodna CSD obdelava | `NP.CSD_DPP_OBDELAVA` po EMŠO; `SY_TISP <> 'B'`; vir navaja prvi zapis in izvoz s `ST_SEZNAM = 5` | EMŠO → obstaja/ne obstaja predhodna obdelava |
| SQL-05 | Dvojnik drugega tipa | `NP.CSD_DPP_PDF`: isti `SF_OSEBE`, drugačen `SF_ODLOCBA_BRANA`, `SF_REZULTAT <> 2` | oseba/tip → dvojnik ali nadaljevanje |
| SQL-06 | Kombinacija izhoda | `TP_OPOMBA` skupaj s `SF_DD_SKLEP_ODLOCBA`; eksplicitno 7.a–7.f in »vse drugo« 7.g; `TP_OPOMBA=01` je virni primer | podatki odločbe → AVT, PIZ ali SD |
| SQL-07 | Smrt osebe | `DG.OSEBA.DT_SMRT` za znani `SF_OSEBE` | obstaja → mrtvi avtomatski izhod; ne obstaja → SD kandidat |

## 3. Procedure, update-i in registracije

### 3.1 `DG.P_POISCI_ZADEVO`

Vir navaja parametre: identifikator, vrsta subjekta, vloga, IN/OUT `ID_ZADEVA`, XML, subjekt, status, akcija in `GUID`.

| Klicni kontekst | Virno navedeni argumenti / rezultat | Učinek |
|---|---|---|
| Osnovna zadeva | `DG.P_POISCI_ZADEVO('DAVČNA ŠTEVILKA CSD LJUBLJANA','P','014-47-1',NULL,NULL,NULL,NULL,NULL,GUID)` | vrne `ID_ZADEVA`; nato `DG.ZADEVA.DT_ZACETEK := DT_PREJEMA` če `SY_TISP <> 'B'` |
| Strokovni delavec | `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-SD',NULL,...,GUID)` | ustvari/poišče SD zadevo; dodelitev po razdelilniku; popravek `DT_ZACETEK` |
| Avtomatska hramba | `DG.P_POISCI_ZADEVO('SF_OSEBE','F','014-47-1-AVT',NULL,...,GUID)` | ustvari/poišče AVT zadevo za PDF in nadaljnji zaključek |

`...` pomeni, da vir v inventarju ne podaja vseh konkretnih vrednosti; diagram jih ne sme izmišljati.

### 3.2 `DG.P_ZAKLJUCI_ZADEVO`

Eksplicitno navedeni klic:

```text
DG.P_ZAKLJUCI_ZADEVO(ID_ZADEVA,3,15248,10,4676,NULL,NULL,NULL)
```

Virna imena parametrov so `IN_ID_ZADEVA`, `IN_ID_RESITEV`, `IN_ID_RESITEV_FAZA_POST`, `IN_ID_FAZA`, `IN_ID_SIGN_ZNAK`, `IN_KONTROLA`, `STATUS`, `OPIS`. V diagramu naj bo označeno kot `call`, ne kot dokaz uspešnega izvajanja v tem okolju.

### 3.3 Registracije `SS.EVIDENTIRANJE_VLOG`

| ID registracije | Vloga / sistem po viru |
|---:|---|
| 86 | `014-47-1` / AVT |
| 87 | `014-47-1-PIZ` / UDG |
| 88 | `014-47-1-SD` / UDG |
| 89 | `014-47-1-AVT` / AVT |

Klasifikacije, stopnje in načini so v izvornem SQL, vendar inventar ne podaja popolne preslikave za vsako registracijo; diagram naj prikaže ID-je in odprto opombo, kjer je potrebno.

## 4. Dokumentni tok UDG/CMOD/PIZ

1. NP proces prebere PDF iz ZIP; ZIP ostane v `EP.PRIPONKE_ODDANE` in se ne pošilja neposredno v CMOD.
2. Pri izhodu, ki dokument evidentira, se ustvari/posodobi zadeva in zapis `DG.DOKUMENT` z `ID_VRSTA_DOK=1341`, `ID_FORMAT=3`, `ID_STATUS=2`; ime PDF je po viru del `TX_ZIP` pred prvim `_`.
3. V `DG.POT_ZADEVE` se dodajo virno navedeni zapisi; PVI se pri AVT poti ne opravi. Natančno mapiranje faz ostane odprto.
4. PDF se pošlje v `Q.SF.CM.LOAD.PDF.SIGN.IN` za CMOD masovni zajem.
5. PIZ pot vključuje `NPPZSS001000.insertPzIzbor` in `ZPIZCPR/setObvestiloWS`; konkretni povratni protokol ni določen.
6. Po paketni obdelavi se sestavi e-poštno poročilo z rezultati; prejemnik ni določen.

## 5. Statusna in podatkovna sled

| Dogodek | Zapis / vrednost |
|---|---|
| pred obdelavo | `NP.CSD_DPP_PDF.SF_REZULTAT = NULL` |
| poslovna/tehnična napaka | `SF_REZULTAT = 2`, virna `TX_OPOMBA`, `DT_OBDELAVA` |
| uspešna hramba/PIZ | `SF_REZULTAT = 1`, `ID_ZADEVA`, `DT_OBDELAVA` |
| znana oseba | `SF_OSEBE` iz natanko enega aktivnega zadetka |
| znana mrtva oseba | `DT_SMRT` iz `DG.OSEBA`, preskok SD |
| vsak zaključen PDF | `DT_OBDELAVA` se zapiše tudi pri napaki |

## 6. Diagram-sledljivost in dovoljene oznake robov

| Tehnični element | Predlagana stran/layout lokacija | Oznaka roba |
|---|---|---|
| EP tabele ↔ NP PDF | 05, levi → srednji stolpec | `read`, `write/update` |
| NP PDF ↔ NP obdelava | 05, NP stolpec | `read`, `deduplicate` |
| NP PDF ↔ DG identiteta/oseba | 03 in 05 | `read` |
| NP ↔ `DG.P_POISCI_ZADEVO` | 05/06 | `call` |
| `DG.P_POISCI_ZADEVO` ↔ `DG.ZADEVA` | 05/06 | `write/return ID_ZADEVA` |
| NP ↔ `DG.DOKUMENT`/`DG.POT_ZADEVE` | 06 | `write` |
| UDG ↔ CMOD queue | 01/06 | `message PDF` |
| PIZ ↔ servisi | 06 | `call` |
| NP ↔ e-pošta | 01/06 | `message report` |

### Odprte tehnične opombe za diagram

- Tip odločbe `4` je veja 7.d, vendar pravilo prepoznave ni popolno.
- Celoten `TP_OPOMBA` šifrant ni podan; ohrani kode 01/03/07/08 in označi preostalo kot »vse ostalo«.
- `DG.POT_ZADEVE` navaja faze 2/5/6/25, vendar popolna preslikava ni potrjena.
- Prejemnik e-pošte in natančen mehanizem UI nista določena.
- Klici so tehnična sled iz navodila, ne izvršilni dokazi iz tega workspace-a.

## 7. Validacijska merila za STEP-005/STEP-006

- Vse tabele in procedure iz `REQ-004`/`REQ-005` so prisotne z vsaj enim poljem, predikatom ali učinkom.
- Vsak integracijski rob ima semantiko `read`, `write/update`, `call` ali `message`.
- Razlika ZIP vs. PDF/CMOD je eksplicitna.
- Statusi in ključni identifikatorji so sledljivi od `NP.CSD_DPP_PDF` do zadeve/dokumenta/poročila.
- Nedoločeni deli so označeni kot odprta vprašanja in niso predstavljeni kot potrjena pravila.
