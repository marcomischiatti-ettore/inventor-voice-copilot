"""
comandi/sweep_guide_rail.py
Modulo vocale: Sweep con Rotaia Guida (SweepFeatures.AddUsingGuideRail).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_sezione_mm = 10.0
    match_d = re.search(r'(?:sezione|diametro)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_sezione_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "diametro_sezione_mm": diametro_sezione_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_sezione_mm"])

    resoconto = {
        "modulo": "SweepFeatures",
        "metodo": "SweepFeatures.AddUsingGuideRail",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0
        assert abs(d_cm - params["diametro_sezione_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: SweepFeatures.AddUsingGuideRail D={d_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_SweepGuideRail")
    try:
        cd = part_doc.ComponentDefinition
        _, profile = crea_schizzo_circolare_centrato(part_doc, params["diametro_sezione_mm"], 3)

        wp_path = cd.WorkPlanes.Item(2)
        sk_path = cd.Sketches.Add(wp_path)
        tg = inv_app.TransientGeometry
        path_line = sk_path.SketchLines.AddByTwoPoints(tg.CreatePoint2d(0, 0), tg.CreatePoint2d(0, mm_to_cm(50.0)))
        path = cd.Features.SweepFeatures.CreatePath(path_line)

        # Guida su WorkPlane 1
        wp_guide = cd.WorkPlanes.Item(1)
        sk_guide = cd.Sketches.Add(wp_guide)
        guide_line = sk_guide.SketchLines.AddByTwoPoints(
            tg.CreatePoint2d(d_cm/2.0, 0), tg.CreatePoint2d(d_cm, mm_to_cm(50.0))
        )
        guide = cd.Features.SweepFeatures.CreatePath(guide_line)

        sweep_feat = cd.Features.SweepFeatures.AddUsingGuideRail(profile, path, guide, kJoinOperation)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Sweep con guida creato con successo: {sweep_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
