Ustvari kompleksen, vendar pregleden draw.io diagram arhitekture spletne trgovine, ki prikazuje celoten proces od oddaje naročila do dostave kupcu.

Diagram naj se bere z leve proti desni in naj vsebuje naslednje logične skupine:

1. **Uporabniški kanali**

   * spletna aplikacija,
   * mobilna aplikacija,
   * administratorski portal.

2. **Vstopna plast**

   * CDN,
   * požarni zid,
   * API Gateway,
   * storitev za avtentikacijo.

3. **Aplikacijske storitve**

   * uporabniški profili,
   * katalog izdelkov,
   * košarica,
   * naročila,
   * plačila,
   * zaloga,
   * obvestila,
   * dostava.

4. **Podatkovna in infrastrukturna plast**

   * podatkovna baza uporabnikov,
   * podatkovna baza izdelkov,
   * podatkovna baza naročil,
   * Redis cache,
   * objektna shramba,
   * message broker,
   * sistem za beleženje dnevnikov in monitoring.

5. **Zunanji sistemi**

   * ponudnik plačil,
   * dostavna služba,
   * ponudnik e-pošte in SMS-sporočil.

Prikaži glavni tok: kupec odpre aplikacijo, se prijavi, pregleduje katalog, doda izdelke v košarico, odda naročilo, izvede plačilo, sistem preveri zalogo, ustvari naročilo, sproži dostavo in pošlje obvestilo kupcu.

Asinhrone dogodke, kot so »naročilo ustvarjeno«, »plačilo potrjeno« in »paket odposlan«, spelji prek message brokerja. Sinhrone API-klice prikaži s polno črto, asinhrone dogodke pa s črtkano črto. Dodaj majhno legendo.

Uporabi vsebnike za logične skupine. Zunanji sistemi naj bodo jasno ločeni od interne arhitekture. Komponente naj bodo razporejene v smiselne plasti in ne smejo biti postavljene samo v eno vrstico.

Povezave naj bodo ortogonalne in ne smejo potekati skozi komponente, naslove ali vsebnike. Zmanjšaj število križanj povezav. Poskrbi za dovolj praznega prostora, enotne dimenzije sorodnih komponent in jasno vizualno hierarhijo.

Če je diagram preobsežen, ga razdeli na dve strani:

* pregled celotne arhitekture,
* podroben proces obdelave naročila.

Pred zaključkom preveri prekrivanja, križanja povezav, odrezano besedilo in nelogične položaje. Nato generiraj veljaven draw.io XML in ustvari končni diagram.
