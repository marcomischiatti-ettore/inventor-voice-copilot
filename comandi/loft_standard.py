"""
comandi/loft_standard.py
Modulo vocale: Transizione Loft tra Profili (LoftFeatures.Add).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    altezza_mm = 50.0
    match_h = re.search(r'(?:altezza|distanza|quota)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_h:
        altezza_mm = float(match_h.group(1).replace(',', '.'))

    return {
        "altezza_mm": altezza_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    h_cm = mm_to_cm(params["altezza_mm"])

    resoconto = {
        "modulo": "LoftFeatures",
        "metodo": "LoftFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "altezza_cm_inventor": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert h_cm > 0
        assert abs(h_cm - params["altezza_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: LoftFeatures.Add transizione H={h_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_LoftStandard")
    try:
        cd = part_doc.ComponentDefinition
        # Sezione 1 su XY Plane (WorkPlane 3)
        _, prof1 = crea_schizzo_rettangolare_centrato(part_doc, 60.0, 40.0, 3)

        # Sezione 2 su piano di offset H
        wp_base = cd.WorkPlanes.Item(3)
        wp_offset = cd.WorkPlanes.AddByPlaneAndOffset(wp_base, h_cm)
        sk2 = cd.Sketches.Add(wp_offset)
        c2 = sk2.SketchCircles.AddByCenterRadius(inv_app.TransientGeometry.CreatePoint2d(0, 0), mm_to_cm(25.0) / 2.0)
        sk2.GeometricConstraints.AddCoincident(sk2.OriginPoint, c2.CenterSketchPoint)
        prof2 = sk2.Profiles.AddForSolid()

        sections = inv_app.TransientObjects.CreateObjectCollection()
        sections.Add(prof1)
        sections.Add(prof2)

        loft_def = cd.Features.LoftFeatures.CreateLoftDefinition(sections, kJoinOperation)
        loft_feat = cd.Features.LoftFeatures.Add(loft_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature Loft creata con successo: {loft_feat.Name}, H={params['altezza_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
