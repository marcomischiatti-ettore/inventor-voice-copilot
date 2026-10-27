# Autodesk Inventor Voice Copilot 🎙️⚙️

Un assistente intelligente vocale e testuale per la modellazione 3D parametrica automatizzata in **Autodesk Inventor**, sviluppato in Python sfruttando le API COM native di Inventor.

Permette di comandare la generazione e modifica di feature 3D direttamente a voce o tramite input testuale in linguaggio naturale.

---

## 🌟 Caratteristiche Principali

- 🗣️ **Comandi Vocali e Testuali in Tempo Reale**: Riconoscimento vocale integrato con microfono o barra di testo interattiva.
- 🎨 **Interfaccia Grafica Moderna (CustomTkinter)**: Console visiva con indicatori di stato, log in tempo reale e switch vocale.
- 📐 **Modellazione Rigorosa e Parametrica**: Rispetta gli standard CAD industriali (`stile_progettazione.md`), gestendo vincoli geometrici al centro/origine, quote parametriche e conversione automatica delle unità di misura (mm/cm).
- 🧩 **Architettura Modulare a Feature**: Ogni comando CAD è isolato in moduli autonomi e testabili (`comandi/`).
- 🤖 **Pipeline AI Integrata**: Moduli di supervisione con Google Gemini (`google-genai`) per la validazione automatica del codice generato e l'analisi dello stile CAD.

---

## 🛠️ Feature CAD Supportate

| Categoria | Comandi Supportati | Esempio Vocale |
| :--- | :--- | :--- |
| **Estrusioni** | Distanza, Passante, Fino a Faccia/Piano, Con Sformo | *"estrusione di 25 mm"*, *"estrusione passante"* |
| **Forature** | Cieco, Passante, Lamato, Svasato, Filettato | *"foro diametro 10 profondo 20"*, *"foro lamato diametro 8"* |
| **Raccordi & Smussi** | Smusso a distanza, distanza/angolo, due distanze; Raccordi bordi | *"smusso di 2 mm"*, *"raccordo raggio 5 mm"* |
| **Serie & Pattern** | Serie Rettangolare, Serie Circolare, Specchiatura | *"serie rettangolare 4 copie passo 30"*, *"serie circolare"* |
| **Feature Avanzate** | Sweep su percorso/guida, Loft, Nervature, Svuotamento (Shell), Spostamento facce | *"svuotamento spessore 2 mm"*, *"nervatura spessore 3"* |
| **Filettature** | Standard metriche e configurazione passo | *"filettatura M10"* |

---

## 📁 Struttura del Repository

```text
├── Avvia_Copilot.bat               # Launcher rapido con un clic per Windows
├── copilot_gui.py                  # Interfaccia grafica CustomTkinter
├── inventor_copilot.py             # Router ed esecutore dei comandi vocali
├── requirements.txt                # Dipendenze Python
├── stile_progettazione.md          # Linee guida e standard di modellazione CAD
├── comandi/                        # Libreria modulare dei comandi Inventor
│   ├── inventor_utils.py           # Connessione COM e utilità di gestione documenti
│   ├── extrude_*.py                # Moduli estrusioni
│   ├── hole_*.py                   # Moduli forature
│   ├── chamfer_*.py / fillet_*.py  # Smussi e raccordi
│   ├── rectangular_pattern.py      # Serie rettangolari
│   ├── circular_pattern.py         # Serie circolari
│   ├── mirror_features.py          # Specchiature
│   └── ...                         # Loft, Sweep, Shell, Rib, Move Face
├── miei_esempi/                    # Esempi di parti CAD (.ipt) di riferimento
├── analizza_stile_da_ipt.py        # Ispezione automatica dello stile da modelli .ipt
└── chiedi_a_gemini.py              # Validatore AI del codice con Google Gemini
```

---

## 🚀 Prerequisiti & Installazione

### 1. Requisiti di Sistema
- **Sistema Operativo**: Windows 10 / 11 (64-bit).
- **CAD**: Autodesk Inventor installato e avviato (qualsiasi versione recente con supporto API COM).
- **Python**: Versione 3.10 o superiore.

### 2. Installazione delle Dipendenze

Clona il repository ed installa i pacchetti richiesti:

```powershell
git clone https://github.com/marcomischiatti-ettore/inventor-voice-copilot.git
cd inventor-voice-copilot
pip install -r requirements.txt
```

> **Nota per il microfono (PyAudio)**: Se l'installazione di `pyaudio` fallisce su Windows tramite pip standard, installare il wheel corrispondente da [PyAudio Wheels](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) oppure via `pip install pipwin; pipwin install pyaudio`.

---

## 🎯 Come Avviare

### Modalità GUI (Consigliata)
Fai doppio clic sul file:
```bat
Avvia_Copilot.bat
```
oppure esegui dal terminale:
```powershell
python copilot_gui.py
```

### Modalità Terminale / Headless
- **Interattiva da riga di comando**:
  ```powershell
  python inventor_copilot.py
  ```
- **Comando singolo**:
  ```powershell
  python inventor_copilot.py "estrusione di 25 mm"
  ```
- **Modalità simulazione** (test parsing senza inviare comandi COM a Inventor):
  ```powershell
  python inventor_copilot.py --simula "foro diametro 10 mm"
  ```

---

## 🔒 Sicurezza & Variabili d'Ambiente

Se intendi utilizzare le funzionalità di revisione AI (`chiedi_a_gemini.py`), imposta la tua chiave API Google Gemini:

```powershell
$env:GEMINI_API_KEY="la_tua_chiave_api"
```

Nessuna chiave viene salvata nel codice sorgente o tracciata su Git (protetta da `.gitignore`).

---

## 🌿 Rami di Sviluppo & Contributi

Il repository segue un flusso di lavoro collaborativo su branch per differenziare le aree di sviluppo:
- **main**: Versione base e condivisa del progetto.
- **simone**: Branch con le implementazioni per lo **Smart Placement parametrico da bordi/spigoli**, selezione interattiva a video (SelectSet), quote visibili nello schizzo, normalizzazione linguistica d'officina e correzione del solido 3D per i fori.  
  👉 Consulta la documentazione dettagliata in [DOCS_BRANCH_SIMONE.md](DOCS_BRANCH_SIMONE.md).

---

## 📄 Licenza

Distribuito sotto licenza **MIT**. Consulta il file `LICENSE` per ulteriori dettagli.
