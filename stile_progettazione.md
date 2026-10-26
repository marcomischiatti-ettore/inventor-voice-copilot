# Stile di Progettazione e Modellazione CAD - Autodesk Inventor Copilot

## 1. Origine e Piani di Riferimento
- **Origine Globale**: Il modello deve essere sempre posizionato e sviluppato in modo simmetrico e centrato sull'Origine globale del sistema di coordinate `(0, 0, 0)`.
- **Piano di Base (Default)**: Utilizzare il piano `XY Plane` (WorkPlane 3) come piano di default per gli schizzi iniziali (vista dall'alto / pianta).
- **Piani di Simmetria**:
  - `YZ Plane` (WorkPlane 1): piano di simmetria laterale (X = 0).
  - `XZ Plane` (WorkPlane 2): piano di simmetria longitudinale (Y = 0).
  - `XY Plane` (WorkPlane 3): piano di base / appoggio (Z = 0).
- **Schizzi**:
  - Le geometrie primarie (es. rettangoli base) devono essere centrate sull'origine (utilizzando un rettangolo con centro nell'origine o vincoli di simmetria/coincidenza rispetto all'asse X, asse Y e punto centrale).
  - Cerchi e perni devono avere il centro vincolato all'origine o posizionati rispetto ad essa.

## 2. Unità di Misura e Conversioni COM
- **Interfaccia Utente & Comandi Vocali**:
  - Le dimensioni specificate dall'utente nei comandi vocali sono espresse in **Millimetri (mm)**.
  - Gli angoli sono espressi in **Gradi (°)**.
- **API COM di Autodesk Inventor**:
  - Inventor memorizza e gestisce internamente tutte le unità di lunghezza in **Centimetri (cm)**.
  - **Regola di conversione obbligatoria**: `lunghezza_inventor_cm = lunghezza_mm / 10.0`.
  - Gli angoli nelle API COM richiedono i **Radianti (rad)**: `angolo_inventor_rad = math.radians(angolo_deg)`.
- Ogni modulo DEVE effettuare esplicitamente questa conversione prima di passare qualsiasi valore a metodi COM o parametri.

## 3. Quotatura e Vincoli Geometrici
- Tutti gli elementi dello schizzo (`PlanarSketch`) devono essere geometricamente vincolati prima dell'operazione di feature (estrusione, rivoluzione, foratura).
- **Convenzioni di quotatura**:
  - Quote principali posizionate rispetto agli assi principali o bordi esterni di riferimento simmetrico.
  - Fori e tasche quotati a partire dai bordi di riferimento o dagli assi di simmetria.
- **Vincoli geometrici obbligatori**:
  - `GeometricConstraints.AddCoincident`: per vincolare centri o spigoli all'origine o assi.
  - `GeometricConstraints.AddSymmetric`: per elementi speculari.
  - `GeometricConstraints.AddHorizontal` / `AddVertical`: per allineamento.

## 4. Denominazione e Gestione Parametri (fx)
- Utilizzare parametri del modello (`ModelParameters`) o parametri utente (`UserParameters`) con nomenclatura semantica autoesplicativa in italiano/inglese standard:
  - `lunghezza`, `larghezza`, `spessore`, `altezza`, `diametro`, `profondita`, `raggio_raccordo`, `smusso`.
- I parametri devono mantenere le unità di misura coerenti (`mm` nel modello utente).

## 5. Gestione Transazioni e Robustezza COM
- Ogni esecuzione di comando vocale deve essere racchiusa all'interno di una transazione Inventor:
  ```python
  trans = inv_app.TransactionManager.StartTransaction(part_doc, "NomeComandoCopilot")
  try:
      # operazioni CAD
      trans.End()
  except Exception as e:
      trans.Abort()
      raise e
  ```
- Questo garantisce l'atomicità: in caso di fallimento o parsing errato, lo stato del modello viene ripristinato tramite `Abort()` senza lasciare schizzi o feature orfane.
