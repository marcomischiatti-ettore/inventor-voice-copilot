"""
comandi/circular_pattern.py
Modulo vocale: Serie Circolare Polare (CircularPatternFeatures.Add).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    conteggio = 6
    angolo_deg = 360.0

    match_c = re.search(r'(\d+)\s*(?:copie|elementi|fori|denti)', f)
    if match_c:
        conteggio = int(match_c.group(1))

    match_a = re.search(r'(?:su|angolo|arco)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:gradi|°|deg))?', f)
    if match_a:
        angolo_deg = float(match_a.group(1).replace(',', '.'))

    return {
        "conteggio": conteggio,
        "angolo_deg": angolo_deg,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    angolo_rad = deg_to_rad(params["angolo_deg"])

    resoconto = {
        "modulo": "CircularPatternFeatures",
        "metodo": "CircularPatternFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "angolo_rad_inventor": angolo_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio"] > 1 and angolo_rad > 0
        assert abs(angolo_rad - math.radians(params["angolo_deg"])) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CircularPatternFeatures.Add N={params['conteggio']} su {angolo_rad:.4f} rad"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_CircularPattern")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_circolare_centrato(part_doc, 80.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(25.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        z_axis = cd.WorkAxes.Item(3) # Z Axis per rivoluzione centrata su XY

        pattern = cd.Features.CircularPatternFeatures.Add(
            feat_coll,
            z_axis,
            True,
            params["conteggio"],
            angolo_rad,
            True # Fit within total angle
        )
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Serie circolare creata: {pattern.Name}, Copie={params['conteggio']}, Angolo={params['angolo_deg']}°"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
