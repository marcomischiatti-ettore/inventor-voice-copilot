"""
comandi/rib_definition.py
Modulo vocale: Definizione Parametrica Nervatura (RibFeatures.CreateRibDefinition).
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
    spessore_mm = 5.0
    match_s = re.search(r'(?:nervatura|costola|spessore)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_s:
        spessore_mm = float(match_s.group(1).replace(',', '.'))

    return {
        "spessore_mm": spessore_mm,
        "direzione_normale": "normale" in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spessore_cm = mm_to_cm(params["spessore_mm"])

    resoconto = {
        "modulo": "RibFeatures",
        "metodo": "RibFeatures.CreateRibDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "spessore_cm_inventor": spessore_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert spessore_cm > 0
        assert abs(spessore_cm - params["spessore_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateRibDefinition spessore={spessore_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_RibDefinition")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        wp2 = cd.WorkPlanes.Item(2)
        sk_rib = cd.Sketches.Add(wp2)
        tg = inv_app.TransientGeometry
        p1 = tg.CreatePoint2d(mm_to_cm(-25.0), mm_to_cm(25.0))
        p2 = tg.CreatePoint2d(mm_to_cm(25.0), mm_to_cm(5.0))
        sk_rib.SketchLines.AddByTwoPoints(p1, p2)
        prof_rib = sk_rib.Profiles.AddForSolid(False)

        rib_def = cd.Features.RibFeatures.CreateRibDefinition(prof_rib, True, spessore_cm)
        rib_feat = cd.Features.RibFeatures.Add(rib_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione nervatura creata: {rib_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
