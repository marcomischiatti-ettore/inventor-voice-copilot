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

## 3. Quotatura e Vincoli Geometrici Obbligatori (Estratti da Esempi Reali IPT)
- **Stato di Vincolo Tassativo**: Ogni schizzo (`PlanarSketch`) deve raggiungere lo stato `sketch.ConstraintStatus == 51713` (`kFullyConstrainedConstraintStatus`), garantendo:
  - Tutte le linee di schizzo diventano **nere** (o colore di entità vincolata secondo il tema Inventor).
  - La barra di stato di Inventor in basso a destra riporta la dicitura **"Completamente vincolato"**.
  - Le quote parametriche grafiche (`DimensionConstraints`) sono **visibili ed editabili** direttamente nel canvas di Inventor (es. `d0 = 100 mm`, `d1 = 80 mm`).
  
- **Tecnica Rettangolo Centrato (da Esempio-002.ipt)**:
  1. Creazione rettangolo con `SketchLines.AddAsTwoPointRectangle(p1, p2)`.
  2. Aggiunta di due diagonali di costruzione (`Construction = True`) congiungenti i vertici opposti (`pt_bl -> pt_tr` e `pt_br -> pt_tl`).
  3. Proiezione del punto d'origine: `proj_origin = sketch.AddByProjectingEntity(ComponentDefinition.WorkPoints.Item(1))`.
  4. Vincolo coincidente tra l'origine proiettata e le due diagonali:
     - `sketch.GeometricConstraints.AddCoincident(proj_origin, diag1)`
     - `sketch.GeometricConstraints.AddCoincident(proj_origin, diag2)`
  5. Quote parametriche grafiche con `sketch.DimensionConstraints.AddTwoPointDistance(..., 19203, text_pt, False)` (larghezza e altezza).
  6. Esecuzione di `sketch.Solve()` per forzare il solver geometrico a consolidare lo stato `51713`.

- **Tecnica Cerchio Centrato**:
  1. Proiezione del punto d'origine: `proj_origin = sketch.AddByProjectingEntity(ComponentDefinition.WorkPoints.Item(1))`.
  2. Creazione cerchio a `(0, 0)` con `SketchCircles.AddByCenterRadius(...)`.
  3. Vincolo coincidente: `sketch.GeometricConstraints.AddCoincident(circle.CenterSketchPoint, proj_origin)`.
  4. Quota diametro: `sketch.DimensionConstraints.AddDiameter(circle, text_pt, False)`.
  5. Esecuzione di `sketch.Solve()`.

- **Regole Standard di Foratura (Aziendali Utente)**:
  - **Default Passante**: Se non diversamente specificato, ogni foro è **SEMPRE PASSANTE** (`AddDrilledByThroughAllExtent`) attraverso l'intero pezzo. Viene realizzato cieco solo se esplicitamente richiesto con la parola *"cieco"* o specificando una profondità numerica.
  - **Filettatura Completa**: Nei fori filettati/maschiati, la filettatura copre sempre **l'intera lunghezza del foro** (`FullTapDepth = True`).
  - **Posizionamento (X, Y)**: Supporto immediato delle coordinate relative all'origine (es. *"x50 y 50"*, *"x: 50 y: 50"*). Se non specificato o se indicato *"al centro"*, il foro viene vincolato rigidamente coincidente all'origine `(0, 0)`.

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
