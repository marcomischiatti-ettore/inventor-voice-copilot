"""
comandi/loft_definition.py
Modulo vocale: Definizione Parametrica Loft Avanzato (LoftFeatures.CreateLoftDefinition).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    distanza_sezioni_mm = 60.0
    match_d = re.search(r'(?:distanza|altezza|quota)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_sezioni_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "distanza_sezioni_mm": distanza_sezioni_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    h_cm = mm_to_cm(params["distanza_sezioni_mm"])

    resoconto = {
        "modulo": "LoftFeatures",
        "metodo": "LoftFeatures.CreateLoftDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "h_cm_inventor": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert h_cm > 0
        assert abs(h_cm - params["distanza_sezioni_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateLoftDefinition sezioni dist={h_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_LoftDefinition")
    try:
        cd = part_doc.ComponentDefinition
        _, prof1 = crea_schizzo_rettangolare_centrato(part_doc, 50.0, 30.0, 3)

        wp_base = cd.WorkPlanes.Item(3)
        wp_offset = cd.WorkPlanes.AddByPlaneAndOffset(wp_base, h_cm)
        sk2 = cd.Sketches.Add(wp_offset)
        r2 = sk2.SketchLines.AddAsTwoPointRectangle(
            inv_app.TransientGeometry.CreatePoint2d(mm_to_cm(-15), mm_to_cm(-15)),
            inv_app.TransientGeometry.CreatePoint2d(mm_to_cm(15), mm_to_cm(15))
        )
        prof2 = sk2.Profiles.AddForSolid()

        sections = inv_app.TransientObjects.CreateObjectCollection()
        sections.Add(prof1)
        sections.Add(prof2)

        loft_def = cd.Features.LoftFeatures.CreateLoftDefinition(sections, kJoinOperation)
        loft_feat = cd.Features.LoftFeatures.Add(loft_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione Loft creata con successo: {loft_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
