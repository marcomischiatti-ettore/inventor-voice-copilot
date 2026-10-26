"""
comandi/chamfer_distance_angle.py
Modulo vocale: Smusso con Distanza e Angolo (ChamferFeatures.AddUsingDistanceAndAngle).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    distanza_mm = 3.0
    angolo_deg = 30.0

    match_d = re.search(r'(?:distanza|smusso)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_mm = float(match_d.group(1).replace(',', '.'))

    match_a = re.search(r'(?:angolo|gradi)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:gradi|°|deg))?', f)
    if match_a:
        angolo_deg = float(match_a.group(1).replace(',', '.'))

    return {
        "distanza_mm": distanza_mm,
        "angolo_deg": angolo_deg,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    dist_cm = mm_to_cm(params["distanza_mm"])
    ang_rad = deg_to_rad(params["angolo_deg"])

    resoconto = {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingDistanceAndAngle",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "dist_cm": dist_cm,
        "ang_rad": ang_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert dist_cm > 0 and ang_rad > 0
        assert abs(dist_cm - params["distanza_mm"]/10.0) < 1e-9
        assert abs(ang_rad - math.radians(params["angolo_deg"])) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: Chamfer AddUsingDistanceAndAngle dist={dist_cm:.4f} cm, ang={ang_rad:.4f} rad"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ChamferDistanceAngle")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(35.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        ref_face = None
        for i in range(1, body.Faces.Count + 1):
            fc = body.Faces.Item(i)
            if hasattr(fc.Geometry, 'Normal') and abs(fc.Geometry.Normal.Z - 1.0) < 0.1:
                ref_face = fc
                break
        if ref_face is None:
            ref_face = body.Faces.Item(1)

        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        for i in range(1, ref_face.Edges.Count + 1):
            edges_coll.Add(ref_face.Edges.Item(i))

        chamfer_feat = cd.Features.ChamferFeatures.AddUsingDistanceAndAngle(edges_coll, ref_face, dist_cm, ang_rad)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Smusso dist/angolo creato con successo: {chamfer_feat.Name}, D={params['distanza_mm']}mm, Ang={params['angolo_deg']}°"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
