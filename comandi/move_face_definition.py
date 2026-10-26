"""
comandi/move_face_definition.py
Modulo vocale: Definizione Spostamento Diretto Faccia (MoveFaceFeatures.CreateMoveFaceDefinition).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    distanza_mm = 6.0
    match_d = re.search(r'(?:distanza|spostamento|trasla)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "distanza_mm": distanza_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    dist_cm = mm_to_cm(params["distanza_mm"])

    resoconto = {
        "modulo": "MoveFaceFeatures",
        "metodo": "MoveFaceFeatures.CreateMoveFaceDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "dist_cm_inventor": dist_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert dist_cm > 0
        assert abs(dist_cm - params["distanza_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateMoveFaceDefinition dist={dist_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_MoveFaceDef")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        faces_coll = inv_app.TransientObjects.CreateFaceCollection()
        faces_coll.Add(body.Faces.Item(1))
        z_axis = cd.WorkAxes.Item(3)

        move_def = cd.Features.MoveFaceFeatures.CreateMoveFaceDefinition(faces_coll)
        move_def.Direction = z_axis
        move_def.Distance = dist_cm
        move_feat = cd.Features.MoveFaceFeatures.Add(move_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione MoveFace completata: {move_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
