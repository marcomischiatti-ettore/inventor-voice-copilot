import os
import sys
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERRORE: Variabile d'ambiente GEMINI_API_KEY non trovata.")
    sys.exit(1)

# Rimuove eventuali etichette/placeholder incollate accidentalmente
prefix = "INCOLLA_QUI_LA_CHIAVE_COPIATA"
if api_key.startswith(prefix):
    api_key = api_key[len(prefix):].strip()

client = genai.Client(api_key=api_key)

if not os.path.exists("report_antigravity.txt"):
    print("ERRORE: report_antigravity.txt mancante.")
    sys.exit(1)

with open("report_antigravity.txt", "r", encoding="utf-8") as f:
    report = f.read()

stile = ""
if os.path.exists("stile_progettazione.md"):
    with open("stile_progettazione.md", "r", encoding="utf-8") as f:
        stile = f.read()

prompt_supervisore = f"""
Sei un Lead CAD Software Architect specializzato nelle API COM di Autodesk Inventor.
L'agente Antigravity ti invia questo resoconto del modulo appena sviluppato o corretto:

{report}

Convenzioni e stile di modellazione obbligatori:
{stile}

Analizza con rigore tecnico:
1. Chiamate COM di Inventor e conversione metrica corretta (Inventor memorizza le lunghezze in centimetri: i mm vanno divisi per 10).
2. Rispetto dei vincoli geometrici, piani di lavoro e parametri definiti in stile_progettazione.md.
3. Robustezza del parsing della frase vocale nell'estrazione dei parametri numerici.

Istruzioni di risposta:
- Se trovi bug, violazioni dello stile o eccezioni COM non gestite, elenca le modifiche tassative per la prossima iterazione.
- Se il modulo è stabile, rispetta lo stile ed è privo di errori, scrivi ESATTAMENTE: 'STATUS: APPROVATO'.
"""

# Modello principale con fallback trasparente sui modelli attivi dell'endpoint Gemini
modelli_da_provare = ["gemini-2.5-pro", "gemini-3-flash-preview", "gemini-flash-latest", "gemini-2.5-flash"]
response = None
for m in modelli_da_provare:
    try:
        response = client.models.generate_content(
            model=m,
            contents=prompt_supervisore
        )
        if response and response.text:
            break
    except Exception as e:
        continue

if not response:
    print("ERRORE durante la generazione del feedback da parte di Gemini.")
    sys.exit(1)

with open("feedback_gemini.txt", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Risposta di Gemini salvata in feedback_gemini.txt")
