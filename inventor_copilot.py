"""
inventor_copilot.py
Interfaccia interattiva e punto di ingresso per Autodesk Inventor Voice Copilot.

Modalità di utilizzo:
1. Interattiva:  python inventor_copilot.py
2. Comando singolo: python inventor_copilot.py "estrusione di 25 mm"
3. Demo 3D live: python inventor_copilot.py --demo
4. Solo simulazione: python inventor_copilot.py --simula "foro diametro 10 mm"
"""

import importlib.util
import os
import re
import sys
from typing import Tuple, Any

try:
    from comandi.inventor_utils import get_inventor_app, get_or_create_part_doc
except ImportError:
    from inventor_utils import get_inventor_app, get_or_create_part_doc

ROUTING_COMANDI = [
    # Extrude
    (r'(?:estrudi|estrusione|estrundi).*?(?:fino\s+a|faccia|superficie|piano\s+offset)', "extrude_to_extent"),
    (r'(?:estrudi|estrusione|estrundi).*?(?:passante|attraverso)', "extrude_through_all"),
    (r'(?:estrudi|estrusione|estrundi).*?(?:sformo|conico|inclinazione)', "extrude_definition"),
    (r'(?:estrudi|estrusione|estrundi|parallelepipedo|blocco|piastra|lastra|cubo|rettangolo)', "extrude_distance"),

    # Hole
    (r'(?:foro|foratura|svas).*?(?:svaso|svasat|conic)', "hole_csink_distance"),
    (r'(?:foro|foratura|lamat).*?(?:lamatur|controforo|testa)', "hole_cbore_distance"),
    (r'(?:foro|foratura).*?(?:passante|attraverso)', "hole_drilled_through_all"),
    (r'(?:foro|foratura).*?(?:filettat|maschiat|avanzat)', "hole_definition"),
    (r'(?:foro|foratura|cieco)', "hole_drilled_distance"),

    # Thread
    (r'(?:configura|imposta).*?(?:filettatura|passo|classe)', "thread_create_info"),
    (r'(?:filetta|filettatura|maschia)', "thread_standard"),

    # Chamfer
    (r'(?:smusso|smussa).*?(?:due\s+distanze|asimmetrico)', "chamfer_two_distances"),
    (r'(?:smusso|smussa).*?(?:angolo|gradi|°)', "chamfer_distance_angle"),
    (r'(?:smusso|smussa)', "chamfer_distance"),

    # Fillet
    (r'(?:raccordo|raccorda).*?(?:avanzat|variabile|corda)', "fillet_definition"),
    (r'(?:raccordo|raccorda|arrotonda)', "fillet_edge_set"),

    # Patterns
    (r'(?:serie|pattern|matrice|ripeti).*?(?:circolare|polare|rotazione|attorno)', "circular_pattern"),
    (r'(?:serie|pattern|matrice|ripeti).*?(?:rettangolare|lineare|griglia)', "rectangular_pattern"),

    # Mirror
    (r'(?:specchia|specchio|mirror|simmetrico)', "mirror_features"),

    # Shell
    (r'(?:svuota|svuotamento|shell|spessore\s+parete)', "shell_standard"),

    # Rib
    (r'(?:nervatura|costola|anima|rinforzo)', "rib_standard"),

    # Move Face
    (r'(?:sposta\s+faccia|trasla\s+faccia|move\s*face)', "move_face_standard"),

    # Loft
    (r'(?:loft|transizione|raccordo\s+tra\s+sezioni)', "loft_standard"),

    # Sweep
    (r'(?:sweep|estrusione\s+lungo|guida)', "sweep_path")
]


def carica_modulo(modulo_id: str):
    path = os.path.join(os.path.dirname(__file__), "comandi", f"{modulo_id}.py")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Modulo '{modulo_id}' non trovato in comandi/")
    spec = importlib.util.spec_from_file_location(modulo_id, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def interpreta_ed_esegui(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Tuple[str, Any]:
    f_lower = frase_vocale.lower().strip()
    target_id = None

    for pattern, mod_id in ROUTING_COMANDI:
        if re.search(pattern, f_lower):
            target_id = mod_id
            break

    if target_id is None:
        target_id = "extrude_distance"

    print(f"\n[COPILOT VOCALE] Elaborazione comando: \"{frase_vocale}\"")
    print(f"[DISPATCHER] Modulo CAD selezionato: {target_id}")

    mod = carica_modulo(target_id)
    func_exec = getattr(mod, "esegui_comando", None)
    if func_exec is None:
        for attr in dir(mod):
            if attr.startswith("esegui_"):
                func_exec = getattr(mod, attr)
                break

    if not func_exec:
        raise AttributeError(f"Funzione di esecuzione non trovata in {target_id}.py")

    # Esecuzione comando
    risultato = func_exec(frase_vocale, test_mode=test_mode, part_doc=part_doc)

    # Se in modalità reale su Inventor, aggiorna la vista 3D (Fit)
    if not test_mode:
        try:
            inv_app = get_inventor_app()
            if inv_app and inv_app.ActiveView:
                inv_app.ActiveView.Fit()
        except Exception:
            pass

    return target_id, risultato


def esegui_demo_live():
    print("\n" + "=" * 65)
    print("AVVIO DEMO LIVE 3D SU AUTODESK INVENTOR")
    print("Guarda lo schermo: Inventor disegnera la geometria passo dopo passo!")
    print("=" * 65)

    inv_app = get_inventor_app()
    if not inv_app:
        print("Errore: Impossibile collegarsi ad Inventor.")
        return

    inv_app.Visible = True
    part_doc = get_or_create_part_doc(inv_app, visible=True)

    sequenza_demo = [
        "crea un rettangolo 100 per 60 ed estrudi di 30 millimetri verso l'alto",
        "fai un foro passante diametro 16 mm al centro",
        "applica uno smusso di 3 mm su tutti gli spigoli"
    ]

    for i, frase in enumerate(sequenza_demo, 1):
        print(f"\n[PASSO {i}/3] Esecuzione: '{frase}'...")
        try:
            _, res = interpreta_ed_esegui(frase, test_mode=False, part_doc=part_doc)
            print(f"-> SUCCESSO: {res['dettagli']}")
        except Exception as e:
            print(f"-> Errore: {e}")

    print("\n" + "=" * 65)
    print("DEMO LIVE COMPLETATA! Puoi vedere il modello 3D generato in Inventor.")
    print("=" * 65)


def avvia_cli_interattiva():
    print("\n" + "=" * 65)
    print("AUTODESK INVENTOR COPILOT - MODALITA' INTERATTIVA LIVE")
    print("=" * 65)
    print("Scrivi comandi in linguaggio naturale (o usa Win+H per dettare col microfono).")
    print("Comandi speciali:")
    print("  'demo'   -> Esegue una sequenza CAD automatica 3D")
    print("  'esci'   -> Chiude il Copilot\n")

    inv_app = get_inventor_app()
    if inv_app:
        inv_app.Visible = True
        print("[STATUS] Connesso ad Autodesk Inventor (Finestra visibile).")
    else:
        print("[STATUS] Attenzione: Inventor non rilevato, sara avviato al primo comando.")

    while True:
        try:
            frase = input("\nInventorCopilot > ").strip()
            if not frase:
                continue
            if frase.lower() in ("esci", "exit", "quit", "q"):
                print("Chiusura Copilot. Arrivederci!")
                break
            if frase.lower() == "demo":
                esegui_demo_live()
                continue

            _, res = interpreta_ed_esegui(frase, test_mode=False)
            if res.get("successo"):
                print(f"[OK] {res['dettagli']}")
            else:
                print(f"[ERRORE] {res.get('errore', 'Operazione non riuscita')}")
        except KeyboardInterrupt:
            print("\nInterrotto dall'utente.")
            break
        except Exception as e:
            print(f"[ERRORE]: {e}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        avvia_cli_interattiva()
    elif args[0] == "--demo":
        esegui_demo_live()
    elif args[0] == "--simula":
        frase = " ".join(args[1:]) if len(args) > 1 else "estrundi di 25 mm"
        interpreta_ed_esegui(frase, test_mode=True)
    else:
        frase = " ".join(args)
        interpreta_ed_esegui(frase, test_mode=False)
