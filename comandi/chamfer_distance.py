"""
comandi/chamfer_distance.py
Modulo vocale: Smusso a Distanza Costante (ChamferFeatures.AddUsingDistance).
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
    distanza_mm = 2.0
    match_d = re.search(r'(?:smusso|smussa|distanza)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "distanza_mm": distanza_mm,
        "tutti_spigoli": "tutti" in f or "completo" in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    distanza_cm = mm_to_cm(params["distanza_mm"])

    resoconto = {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingDistance",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "distanza_cm_inventor": distanza_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert distanza_cm > 0
        assert abs(distanza_cm - params["distanza_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: ChamferFeatures.AddUsingDistance dist={distanza_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ChamferDistance")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 70.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        # Seleziona spigoli superiori
        for i in range(1, body.Edges.Count + 1):
            edge = body.Edges.Item(i)
            edges_coll.Add(edge)
            if not params["tutti_spigoli"] and edges_coll.Count >= 4:
                break

        chamfer_feat = cd.Features.ChamferFeatures.AddUsingDistance(edges_coll, distanza_cm)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Smusso creato con successo: {chamfer_feat.Name}, Dist={params['distanza_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
