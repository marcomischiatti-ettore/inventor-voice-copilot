"""
comandi/hole_drilled_through_all.py
Modulo vocale: Foro Passante Semplice (HoleFeatures.AddDrilledByThroughAllExtent).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kPositiveExtentDirection, kSymmetricExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kPositiveExtentDirection, kSymmetricExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = 10.0
    match_m = re.search(r'\bm(\d+(?:[.,]\d+)?)\b', f)
    if match_m:
        diametro_mm = float(match_m.group(1).replace(',', '.'))
    else:
        match_d = re.search(r'(?:diametro|d|foro)?(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))', f)
        if match_d:
            diametro_mm = float(match_d.group(1).replace(',', '.'))
        else:
            match_d2 = re.search(r'(?:diametro|d|foro)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)', f)
            if match_d2:
                diametro_mm = float(match_d2.group(1).replace(',', '.'))

    pos_x_mm, pos_y_mm = 0.0, 0.0
    match_x = re.search(r'\bx\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)
    match_y = re.search(r'\by\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)
    if match_x:
        pos_x_mm = float(match_x.group(1).replace(',', '.'))
    if match_y:
        pos_y_mm = float(match_y.group(1).replace(',', '.'))

    direzione = kPositiveExtentDirection
    if "entrambi" in f or "simmetric" in f:
        direzione = kSymmetricExtentDirection

    return {
        "diametro_mm": diametro_mm,
        "pos_x_mm": pos_x_mm,
        "pos_y_mm": pos_y_mm,
        "direzione": direzione,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    diametro_cm = mm_to_cm(params["diametro_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddDrilledByThroughAllExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "diametro_cm_inventor": diametro_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert diametro_cm > 0
        assert abs(diametro_cm - (params["diametro_mm"] / 10.0)) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: AddDrilledByThroughAllExtent D={diametro_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleDrilledThroughAll")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(40.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        target_face = None
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, 'Normal') and abs(f.Geometry.Normal.Z - 1.0) < 0.1:
                target_face = f
                break
        if target_face is None:
            target_face = body.Faces.Item(1)

        sk = cd.Sketches.Add(target_face)
        pt2d = inv_app.TransientGeometry.CreatePoint2d(mm_to_cm(params["pos_x_mm"]), mm_to_cm(params["pos_y_mm"]))
        sp = sk.SketchPoints.Add(pt2d)
        if abs(params["pos_x_mm"]) < 1e-6 and abs(params["pos_y_mm"]) < 1e-6:
            try:
                sk.GeometricConstraints.AddCoincident(sk.OriginPoint, sp)
            except Exception:
                pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        place_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(coll)
        hole_feat = cd.Features.HoleFeatures.AddDrilledByThroughAllExtent(place_def, diametro_cm, params["direzione"])

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro passante creato con successo: {hole_feat.Name}, D={params['diametro_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
