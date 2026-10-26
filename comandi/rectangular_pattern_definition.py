"""
comandi/rectangular_pattern_definition.py
Modulo vocale: Definizione Serie Rettangolare Avanzata (RectangularPatternFeatures.CreateDefinition).
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
    conteggio = 4
    passo_mm = 25.0
    match_c = re.search(r'(\d+)\s*(?:copie|elementi)', f)
    if match_c:
        conteggio = int(match_c.group(1))
    match_p = re.search(r'(?:passo|spaziatura|distanza)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_p:
        passo_mm = float(match_p.group(1).replace(',', '.'))

    return {
        "conteggio": conteggio,
        "passo_mm": passo_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    passo_cm = mm_to_cm(params["passo_mm"])

    resoconto = {
        "modulo": "RectangularPatternFeatures",
        "metodo": "RectangularPatternFeatures.CreateDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "passo_cm": passo_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio"] > 1 and passo_cm > 0
        assert abs(passo_cm - params["passo_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: RectangularPatternDefinition N={params['conteggio']}, Passo={passo_cm} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_RectPatternDef")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 100.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(25.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        x_axis = cd.WorkAxes.Item(1)

        pat_def = cd.Features.RectangularPatternFeatures.CreateDefinition(
            feat_coll, x_axis, True, params["conteggio"], passo_cm, 20737
        )
        pattern = cd.Features.RectangularPatternFeatures.AddByDefinition(pat_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione serie rettangolare creata con successo: {pattern.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
