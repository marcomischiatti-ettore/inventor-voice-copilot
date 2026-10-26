"""
comandi/extrude_distance.py
Modulo per il comando vocale: Estrusione a Distanza (ExtrudeFeatures.AddByDistanceExtent).

Soddisfa rigorosamente stile_progettazione.md:
- Conversione metrica millimetri -> centimetri (mm / 10.0)
- Origine e simmetria centrata su WorkPlane XY (WorkPlane 3)
- Gestione transazioni atomiche con TransactionManager
"""

import math
import os
import re
import sys
from typing import Dict, Any, Optional

try:
    from comandi.inventor_utils import (
        mm_to_cm,
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
    Estrae i parametri di estrusione da una frase in linguaggio naturale.
    Supporta varianti di formulazione, unità esplicite o implicite (mm), direzioni e operazioni.
    """
    f = frase.lower().strip()
    
    # 1. Estrazione direzione
    direzione = kPositiveExtentDirection
    if "simmetric" in f:
        direzione = kSymmetricExtentDirection
    elif "negativ" in f or "verso il basso" in f or "sotto" in f or "oppost" in f:
        direzione = kNegativeExtentDirection
    elif "positiv" in f or "verso l'alto" in f or "sopra" in f:
        direzione = kPositiveExtentDirection

    # 2. Estrazione operazione booleana
    operazione = kJoinOperation
    if "tagli" in f or "rimuov" in f or "scav" in f or "asport" in f:
        operazione = kCutOperation
    elif "intersec" in f:
        operazione = kIntersectOperation
    elif "nuovo corpo" in f:
        operazione = kNewBodyOperation

    # 3. Estrazione dimensioni base e altezza (es. "100x100x10", "100x50", "base 100 per 50")
    larghezza_base = 50.0  # default mm
    altezza_base = 30.0   # default mm
    distanza_mm = 20.0    # default mm

    # 1. Match 3D tipo '200x100x10' o '200 per 100 per 10'
    match_3d = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:per|x|\*)\s*(\d+(?:[.,]\d+)?)\s*(?:per|x|\*)\s*(\d+(?:[.,]\d+)?)', f)
    if match_3d:
        larghezza_base = float(match_3d.group(1).replace(',', '.'))
        altezza_base = float(match_3d.group(2).replace(',', '.'))
        distanza_mm = float(match_3d.group(3).replace(',', '.'))
    else:
        # 2. Match spessore con prefissi tecnici: sp, sp., spessore, thk, s, h, alt, prof
        # Es. 'piastra 200x100 sp10', 'sp. 10', 's10', 'spessore 10'
        match_sp = re.search(r'\b(?:sp|sp\.|spessore|spess|thk|s|alt|altezza|h|prof|profondit[àa])\s*[:=.]?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?\b', f)
        if match_sp:
            distanza_mm = float(match_sp.group(1).replace(',', '.'))

        # 3. Match 2D base x altezza
        match_dim_rett = re.search(r'(?:base|rettangolo|profilo|piastra|lastra)?\s*(\d+(?:[.,]\d+)?)\s*(?:per|x|\*)\s*(\d+(?:[.,]\d+)?)', f)
        if match_dim_rett:
            larghezza_base = float(match_dim_rett.group(1).replace(',', '.'))
            altezza_base = float(match_dim_rett.group(2).replace(',', '.'))

        if not match_sp:
            patterns_distanza = [
                r'(?:estrundi|estrusione|estrudi|distanza|lunghezza)(?:\s+di|\s+a)?\s+(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?',
                r'(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)\s*(?:di\s+estrusione|in\s+altezza|in\s+profondit[àa])?',
                r'(?:di\s+)?(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)'
            ]
            for pat in patterns_distanza:
                m = re.search(pat, f)
                if m:
                    val = float(m.group(1).replace(',', '.'))
                    if match_dim_rett and (val == larghezza_base or val == altezza_base):
                        continue
                    distanza_mm = val
                    break

    return {
        "distanza_mm": distanza_mm,
        "direzione": direzione,
        "operazione": operazione,
        "larghezza_base_mm": larghezza_base,
        "altezza_base_mm": altezza_base,
        "frase_originale": frase
    }


def esegui_estrusione(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    """
    Interpreta il comando vocale ed esegue l'estrusione via COM su Autodesk Inventor.
    Se test_mode è True o in ambiente senza Inventor attivo, simula la chiamata validando i parametri.
    """
    parametri = analizza_frase_vocale(frase_vocale)
    distanza_mm = parametri["distanza_mm"]
    direzione = parametri["direzione"]
    operazione = parametri["operazione"]
    
    # Conversione obbligatoria mm -> cm per le API COM di Inventor
    distanza_cm = mm_to_cm(distanza_mm)
    
    resoconto = {
        "modulo": "ExtrudeFeatures",
        "metodo": "ExtrudeFeatures.AddByDistanceExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": parametri,
        "distanza_mm": distanza_mm,
        "distanza_cm_inventor": distanza_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert distanza_cm > 0, "La distanza in centimetri deve essere strettamente positiva"
        assert abs(distanza_cm - (distanza_mm / 10.0)) < 1e-9, "Errore di conversione metrica: mm/10 != cm"
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: ExtrudeFeatures.AddByDistanceExtent(Profile, {distanza_cm:.4f} cm, dir={direzione}, op={operazione})"
        return resoconto

    # Esecuzione reale tramite Inventor COM
    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Autodesk Inventor.")

    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans_manager = inv_app.TransactionManager
    transazione = trans_manager.StartTransaction(part_doc, "Copilot_ExtrudeDistance")

    try:
        cd = part_doc.ComponentDefinition
        
        # Recupera profilo esistente dall'ultimo schizzo o creane uno simmetrico centrato sull'origine XY
        profile = None
        for i in range(cd.Sketches.Count, 0, -1):
            sk = cd.Sketches.Item(i)
            if not sk.Consumed and sk.Profiles.Count > 0:
                profile = sk.Profiles.Item(1)
                break
        
        if profile is None:
            _, profile = crea_schizzo_rettangolare_centrato(
                part_doc, 
                larghezza_mm=parametri["larghezza_base_mm"], 
                altezza_mm=parametri["altezza_base_mm"],
                piano_indice=3
            )

        # Chiamata API COM nativa
        extrude_feat = cd.Features.ExtrudeFeatures.AddByDistanceExtent(
            profile,
            distanza_cm,
            direzione,
            operazione
        )

        transazione.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature creata con successo: {extrude_feat.Name}, Base: {parametri['larghezza_base_mm']}x{parametri['altezza_base_mm']} mm, Spessore: {distanza_mm} mm"
        return resoconto

    except Exception as e:
        transazione.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e

# Alias per compatibilità router
esegui_comando = esegui_estrusione
