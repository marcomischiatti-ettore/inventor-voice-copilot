"""
comandi/circular_pattern_definition.py
Modulo vocale: Definizione Serie Circolare Avanzata (CircularPatternFeatures.CreateDefinition).
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

# Enum PatternComputeType
kIdenticalCompute = 13313
kAdjustToModelCompute = 13314
kOptimizedCompute = 13315


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().replace(',', '.')
    # Estrazione Conteggio (default 8)
    match_c = re.search(r'(\d+)\s*(?:copie|elementi|fori|pezzi|n=)', f)
    conteggio = int(match_c.group(1)) if match_c else 8
    
    # Estrazione Angolo (cerca gradi o deg, default 360)
    match_a = re.search(r'(\d+(?:\.\d+)?)\s*(?:gradi|deg|°)', f)
    angolo_deg = float(match_a.group(1)) if match_a else 360.0
    
    return {
        "conteggio": conteggio,
        "angolo_deg": angolo_deg,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    ang_rad = deg_to_rad(params["angolo_deg"])

    resoconto = {
        "modulo": "CircularPatternFeatures",
        "metodo": "CircularPatternFeatures.CreateDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "angolo_rad_inventor": ang_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio"] > 1 and ang_rad > 0
        assert abs(ang_rad - math.radians(params["angolo_deg"])) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CircularPatternDefinition N={params['conteggio']}, Ang={ang_rad:.4f} rad, ComputeType={kIdenticalCompute}"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_circular_pattern_definition")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_circolare_centrato(part_doc, 80.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(25.0), kPositiveExtentDirection, kJoinOperation)

        # Seleziona l'ultima feature creata
        target_feat = cd.Features.Item(cd.Features.Count)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        z_axis = cd.WorkAxes.Item(3)

        pat_def = cd.Features.CircularPatternFeatures.CreateDefinition(
            feat_coll, z_axis, True, params["conteggio"], ang_rad, kIdenticalCompute
        )
        pattern = cd.Features.CircularPatternFeatures.AddByDefinition(pat_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione serie circolare creata con successo: {pattern.Name}, Copie={params['conteggio']}, Angolo={params['angolo_deg']}°"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
