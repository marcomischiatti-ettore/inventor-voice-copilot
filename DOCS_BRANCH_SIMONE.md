# Documentazione Sviluppo - Branch `simone`

Questo documento descrive le migliorie, le architetture introdotte e le correzioni implementate nel branch **`simone`**, a beneficio degli altri sviluppatori e collaboratori del progetto **Autodesk Inventor Voice Copilot**.

---

## 📌 Panoramica del Branch `simone`
Il branch `simone` introduce il supporto allo **Smart Placement parametrico** per le lavorazioni di foratura e svuotamento in Autodesk Inventor, risolvendo le limitazioni del posizionamento fisso all'origine o al centro faccia e correggendo le criticità riscontrate nella creazione fisica delle feature 3D.

---

## 🚀 Nuove Funzionalità & Migliorie Implementate

### 1. Smart Placement dei Fori da Spigoli/Bordi (`comandi/inventor_utils.py`)
In precedenza, i fori venivano creati esclusivamente al centro della faccia o tramite coordinate cartesiane assolute rispetto all'origine globale.
Nel branch `simone` è stato implementato l'algoritmo di **posizionamento relativo ai bordi del solido**:
- **Estrazione geometrica dei contorni (`EdgeLoops.Item(1)`)**: Isola il loop perimetrale esterno del solido, ignorando eventuali bordi interni generati da fori o asole preesistenti.
- **Calcolo coordinate cartesiane nello schizzo**: A partire dalle dimensioni reali della faccia (`min_u`, `max_u`, `min_v`, `max_v`), calcola l'offset richiesto dall'utente:
  - *Sinistra / Sinistro*: `min_u + offset`
  - *Destra / Destro*: `max_u - offset`
  - *Fondo / Basso / Sotto / Inferiore*: `min_v + offset`
  - *Alto / Sopra / Superiore*: `max_v - offset`
- **Quote parametriche visibili**: Lo schizzo proietta gli spigoli di riferimento con `AddByProjectingEntity` e applica vincoli di quota parametrica (`AddTwoPointDistance`), permettendo all'utente di modificare le quote direttamente dall'interfaccia di Inventor.

### 2. Selezione Interattiva a Video (`SelectSet`)
Se l'utente seleziona una specifica faccia o spigolo a video in Autodesk Inventor prima di pronunciare o digitare il comando, il sistema dà priorità alla selezione attiva (`part_doc.SelectSet`), applicando la lavorazione direttamente sull'entità selezionata.

### 3. Svuotamento Semantico (`comandi/shell_standard.py`)
Lo strumento di svuotamento (Shell) supporta ora l'indicazione semantica della faccia da rimuovere:
- *"svuotamento 2 mm rimuovi faccia superiore"* (o frontale, inferiore, posteriore, ecc.).
- Se nessuna faccia è indicata ma l'utente ne ha selezionata una a video, viene rimossa la faccia selezionata.

### 4. Normalizzazione del Linguaggio d'Officina (`normalizza_frase`)
Per gestire il gergo tecnico e le abbreviazioni frequenti usate nella modellazione meccanica e nei comandi vocali, è stato integrato un motore di normalizzazione preliminare in `inventor_utils.py`:
- **Abbreviazioni diametro**: `diam.`, `diam`, `d.`, `ø`, `fi` $\rightarrow$ `diametro`
- **Direzioni abbreviate**: `sx` $\rightarrow$ `sinistra`, `dx` $\rightarrow$ `destra`, `sup` $\rightarrow$ `superiore`, `inf` $\rightarrow$ `inferiore`
- **Separazione unità incollate**: es. `20mm` $\rightarrow$ `20 mm`, `10cm` $\rightarrow$ `10 cm`
- **Preposizioni articolate d'officina**: `dall'alto`, `dallalto`, `dal fondo`, `dal basso`, `dal sotto`, `dalla sinistra`, `dalla destra` normalizzate per garantire il corretto matching delle espressioni regolari.

---

## 🐛 Bug Critici Risolti

### 1. Mancata Asportazione del Solido nei Fori (Vettore di Foratura)
- **Problema**: Lo schizzo del foro veniva creato e posizionato correttamente, ma la feature nell'albero delle lavorazioni di Inventor rimaneva incompleta/in errore senza tagliare il solido 3D.
- **Causa**: Il parametro di direzione passato alle API Inventor (`AddDrilledByThroughAllExtent` e `AddDrilledByDistanceExtent`) era impostato su `kNegativeExtentDirection` (`20994`), che puntava il vettore di foratura verso l'esterno del solido (nel vuoto).
- **Risoluzione**: Ripristinato **`kPositiveExtentDirection` (`20993`)**, che in Inventor rappresenta la normale entrante nel materiale quando lo schizzo giace su una faccia planare del solido.

### 2. Forzatura Aggiornamento Documento CAD (`Update2`)
- **Problema**: Dopo il completamento della transazione, le feature potevano rimanere in uno stato di anteprima pendente.
- **Risoluzione**: Aggiunta la chiamata obbligatoria `part_doc.Update2(True)` (con fallback su `part_doc.Update()`) subito dopo `trans.End()` in tutti i moduli di foratura.

### 3. Priorità di Routing Fori Passanti vs Ciechi
- In `inventor_copilot.py`, l'ordine delle regole di routing è stato allineato a `stile_progettazione.md`: i fori sono passanti di default a meno che non siano esplicitamente specificati termini come `cieco`, `profondo`, `profondità`, `filettato`, `lamato` o `svasato`.

---

## 🧪 Esempi di Comandi Testati con Successo

- `foro da 20 passante a 10 mm da destra e 20 mm da sotto`
- `foro diam.20 passante a 30 mm da dx e 30 mm dal fondo`
- `fai un foro Diametro 15 profondo 5 30 mm da sinistra e 30 mm dallalto`
- `svuotamento spessore 2 mm rimuovi faccia superiore`
- `foro diametro 10 al centro`

---

## 🔀 Come Integrare o Provare il Branch `simone`

Per testare o fare il merge di questo branch in locale:

```powershell
# Scaricare tutti i branch remoti
git fetch origin

# Passare al branch simone
git checkout simone

# Oppure eseguire il merge nel proprio branch / main
git merge simone
```
