"""
comandi/move_face_standard.py
Modulo vocale: Spostamento Diretto Facce (MoveFaceFeatures.Add).
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
    spostamento_mm = 5.0
    match_s = re.search(r'(?:sposta|trasla|offset|distanza)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_s:
        spostamento_mm = float(match_s.group(1).replace(',', '.'))

    return {
        "spostamento_mm": spostamento_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spost_cm = mm_to_cm(params["spostamento_mm"])

    resoconto = {
        "modulo": "MoveFaceFeatures",
        "metodo": "MoveFaceFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "spost_cm_inventor": spost_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert spost_cm > 0
        assert abs(spost_cm - params["spostamento_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: MoveFaceFeatures.Add spost={spost_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_MoveFaceStandard")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        faces_coll = inv_app.TransientObjects.CreateFaceCollection()
        for i in range(1, body.Faces.Count + 1):
            fc = body.Faces.Item(i)
            if hasattr(fc.Geometry, 'Normal') and abs(fc.Geometry.Normal.Z - 1.0) < 0.1:
                faces_coll.Add(fc)
                break
        if faces_coll.Count == 0:
            faces_coll.Add(body.Faces.Item(1))

        z_axis = cd.WorkAxes.Item(3)
        move_def = cd.Features.MoveFaceFeatures.CreateMoveFaceDefinition(faces_coll)
        move_def.Direction = z_axis
        move_def.Distance = spost_cm
        move_feat = cd.Features.MoveFaceFeatures.Add(move_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Spostamento faccia completato: {move_feat.Name}, Spost={params['spostamento_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
