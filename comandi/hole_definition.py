"""
comandi/hole_definition.py
Modulo vocale: Definizione Avanzata di Foratura (HoleFeatures.CreateHoleDefinition).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = 10.0
    profondita_mm = 20.0
    passante = "passante" in f or "attraverso" in f

    match_d = re.search(r'(?:diametro|d|m|foro)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_mm = float(match_d.group(1).replace(',', '.'))

    match_prof = re.search(r'(?:profondit[àa]|profondo)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_prof:
        profondita_mm = float(match_prof.group(1).replace(',', '.'))

    return {
        "diametro_mm": diametro_mm,
        "profondita_mm": profondita_mm,
        "passante": passante,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_mm"])
    h_cm = mm_to_cm(params["profondita_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.CreateHoleDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "h_cm": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0 and h_cm > 0
        assert abs(d_cm - params["diametro_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: HoleDefinition parametrica D={d_cm:.4f} cm, H={h_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleDefinition")
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
        sp = sk.SketchPoints.Add(inv_app.TransientGeometry.CreatePoint2d(0, 0))
        try:
            sk.GeometricConstraints.AddCoincident(sk.OriginPoint, sp)
        except Exception:
            pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        place_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(coll)
        if params["passante"]:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByThroughAllExtent(place_def, d_cm, kNegativeExtentDirection)
        else:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByDistanceExtent(place_def, d_cm, h_cm, kNegativeExtentDirection, False, deg_to_rad(118.0))

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature foratura avanzata creata con successo: {hole_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
