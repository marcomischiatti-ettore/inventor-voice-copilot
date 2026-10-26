"""
comandi/extrude_definition.py
Modulo per il comando vocale: Definizione Avanzata di Estrusione con Sformo (ExtrudeFeatures.CreateExtrudeDefinition).

Rispettando rigorosamente stile_progettazione.md:
- Conversione metrica millimetri -> centimetri (mm / 10.0) per distanze
- Conversione angolare gradi -> radianti (math.radians) per sformo (TaperAngle)
- Geometria simmetrica centrata su WorkPlane XY (WorkPlane 3)
- Transazionalità atomica tramite TransactionManager
"""

import math
import os
import re
import sys
from typing import Dict, Any, Optional

try:
    from comandi.inventor_utils import (
        mm_to_cm,
        deg_to_rad,
        get_inventor_app,
        get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection,
        kNegativeExtentDirection,
        kSymmetricExtentDirection,
        kJoinOperation,
        kCutOperation,
        kIntersectOperation,
        kNewBodyOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm,
        deg_to_rad,
        get_inventor_app,
        get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection,
        kNegativeExtentDirection,
        kSymmetricExtentDirection,
        kJoinOperation,
        kCutOperation,
        kIntersectOperation,
        kNewBodyOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    """
    Estrae i parametri per la definizione avanzata di estrusione:
    distanza (mm), angolo di sformo (gradi), direzione, operazione booleana.
    """
    f = frase.lower().strip()

    # 1. Direzione estrusione
    direzione = kPositiveExtentDirection
    if "simmetric" in f:
        direzione = kSymmetricExtentDirection
    elif "negativ" in f or "verso il basso" in f or "in giu" in f or "in giù" in f:
        direzione = kNegativeExtentDirection
    elif "positiv" in f or "verso l'alto" in f or "in su" in f:
        direzione = kPositiveExtentDirection

    # 2. Operazione booleana
    operazione = kJoinOperation
    if "tagli" in f or "scav" in f or "asport" in f:
        operazione = kCutOperation
    elif "intersec" in f:
        operazione = kIntersectOperation
    elif "nuovo corpo" in f:
        operazione = kNewBodyOperation

    # 3. Angolo di sformo (in gradi)
    angolo_sformo_deg = 0.0
    match_sformo = re.search(r'(?:sformo|angolo|taper)(?:\s*(?:di|a))?\s*(-?\d+(?:[.,]\d+)?)(?:\s*(?:gradi|°|deg))?', f)
    if match_sformo:
        angolo_sformo_deg = float(match_sformo.group(1).replace(',', '.'))

    # 4. Distanza/profondità di estrusione
    distanza_mm = 25.0
    patterns_distanza = [
        r'(?:estrundi|estrusione|estrudi|altezza|profondit[àa]|spessore)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?',
        r'(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)\s*(?:di\s+estrusione|in\s+altezza)?',
        r'(?:di\s+)?(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)'
    ]
    for pat in patterns_distanza:
        m = re.search(pat, f)
        if m:
            val = float(m.group(1).replace(',', '.'))
            # Ignora se è il valore dello sformo
            if match_sformo and abs(val - abs(angolo_sformo_deg)) < 1e-4:
                continue
            distanza_mm = val
            break

    return {
        "distanza_mm": distanza_mm,
        "angolo_sformo_deg": angolo_sformo_deg,
        "direzione": direzione,
        "operazione": operazione,
        "frase_originale": frase
    }


def esegui_estrusione_avanzata(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    """
    Configura ed esegue l'estrusione avanzata tramite ExtrudeFeatures.CreateExtrudeDefinition.
    """
    parametri = analizza_frase_vocale(frase_vocale)
    distanza_mm = parametri["distanza_mm"]
    angolo_deg = parametri["angolo_sformo_deg"]
    direzione = parametri["direzione"]
    operazione = parametri["operazione"]

    # Conversioni obbligatorie: mm -> cm, deg -> rad
    distanza_cm = mm_to_cm(distanza_mm)
    angolo_rad = deg_to_rad(angolo_deg)

    resoconto = {
        "modulo": "ExtrudeFeatures",
        "metodo": "ExtrudeFeatures.CreateExtrudeDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": parametri,
        "distanza_cm_inventor": distanza_cm,
        "angolo_rad_inventor": angolo_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert distanza_cm > 0, "Distanza in centimetri deve essere positiva"
        assert abs(distanza_cm - (distanza_mm / 10.0)) < 1e-9, "Errore conversione metrica: mm/10 != cm"
        assert abs(angolo_rad - math.radians(angolo_deg)) < 1e-9, "Errore conversione angolare in radianti"
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateExtrudeDefinition con dist={distanza_cm:.4f} cm, sformo={angolo_rad:.4f} rad"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Autodesk Inventor.")

    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans_manager = inv_app.TransactionManager
    transazione = trans_manager.StartTransaction(part_doc, "Copilot_ExtrudeDefinition")

    try:
        cd = part_doc.ComponentDefinition

        # Recupera o crea profilo simmetrico centrato su XY Plane (WorkPlane 3)
        profile = None
        for i in range(cd.Sketches.Count, 0, -1):
            sk = cd.Sketches.Item(i)
            if not sk.Consumed and sk.Profiles.Count > 0:
                profile = sk.Profiles.Item(1)
                break

        if profile is None:
            _, profile = crea_schizzo_rettangolare_centrato(part_doc, 60.0, 40.0, piano_indice=3)

        # 1. Creazione ExtrudeDefinition tramite COM
        extrude_defn = cd.Features.ExtrudeFeatures.CreateExtrudeDefinition(profile, operazione)

        # 2. Configurazione estensione a distanza
        extrude_defn.SetDistanceExtent(distanza_cm, direzione)

        # 3. Configurazione angolo di sformo in radianti
        if abs(angolo_rad) > 1e-9:
            extrude_defn.TaperAngle = angolo_rad

        # 4. Creazione feature
        extrude_feat = cd.Features.ExtrudeFeatures.Add(extrude_defn)

        transazione.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature avanzata creata con successo: {extrude_feat.Name}, Sformo: {angolo_deg}° ({angolo_rad:.4f} rad)"
        return resoconto

    except Exception as e:
        transazione.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e


if __name__ == "__main__":
    frasi = [
        "estrusione avanzata di 30 mm con sformo di 5 gradi",
        "estrudi 40 mm con angolo di sformo -3 gradi",
        "taglio estruso di 15 mm sformo 2 gradi verso il basso"
    ]
    print("=== TEST PARSING E SIMULAZIONE EXTRUDE_DEFINITION ===")
    for f in frasi:
        res = esegui_estrusione_avanzata(f, test_mode=True)
        print(f"Frase: '{f}' -> Dist: {res['distanza_cm_inventor']} cm, Sformo: {res['angolo_rad_inventor']} rad")
