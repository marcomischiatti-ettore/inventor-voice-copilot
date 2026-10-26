"""
comandi/chamfer_two_distances.py
Modulo vocale: Smusso a Due Distanze Asimmetriche (ChamferFeatures.AddUsingTwoDistances).
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
    dist1_mm = 2.0
    dist2_mm = 5.0

    match_d = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:per|x|e)\s*(\d+(?:[.,]\d+)?)', f)
    if match_d:
        dist1_mm = float(match_d.group(1).replace(',', '.'))
        dist2_mm = float(match_d.group(2).replace(',', '.'))

    return {
        "distanza_1_mm": dist1_mm,
        "distanza_2_mm": dist2_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d1_cm = mm_to_cm(params["distanza_1_mm"])
    d2_cm = mm_to_cm(params["distanza_2_mm"])

    resoconto = {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingTwoDistances",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d1_cm": d1_cm,
        "d2_cm": d2_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d1_cm > 0 and d2_cm > 0
        assert abs(d1_cm - params["distanza_1_mm"]/10.0) < 1e-9
        assert abs(d2_cm - params["distanza_2_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: AddUsingTwoDistances D1={d1_cm:.4f} cm, D2={d2_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ChamferTwoDistances")
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

        chamfer_feat = cd.Features.ChamferFeatures.AddUsingTwoDistances(edges_coll, ref_face, d1_cm, d2_cm)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Smusso a due distanze creato: {chamfer_feat.Name}, D1={params['distanza_1_mm']}mm, D2={params['distanza_2_mm']}mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
