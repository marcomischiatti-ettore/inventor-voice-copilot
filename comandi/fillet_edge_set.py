"""
comandi/fillet_edge_set.py
Modulo vocale: Raccordo a Raggio Costante (FilletFeatures.AddEdgeSet).
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
    raggio_mm = 3.0
    match_r = re.search(r'(?:raccordo|raccorda|raggio|r)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_r:
        raggio_mm = float(match_r.group(1).replace(',', '.'))

    return {
        "raggio_mm": raggio_mm,
        "tutti_spigoli": "tutti" in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    raggio_cm = mm_to_cm(params["raggio_mm"])

    resoconto = {
        "modulo": "FilletFeatures",
        "metodo": "FilletFeatures.AddEdgeSet",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "raggio_cm_inventor": raggio_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert raggio_cm > 0
        assert abs(raggio_cm - params["raggio_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: FilletFeatures.AddEdgeSet R={raggio_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_FilletEdgeSet")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        for i in range(1, body.Edges.Count + 1):
            edges_coll.Add(body.Edges.Item(i))
            if not params["tutti_spigoli"] and edges_coll.Count >= 4:
                break

        fillet_feat = cd.Features.FilletFeatures.AddEdgeSet(edges_coll, raggio_cm)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Raccordo creato con successo: {fillet_feat.Name}, R={params['raggio_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
