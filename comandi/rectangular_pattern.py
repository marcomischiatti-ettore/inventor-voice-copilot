"""
comandi/rectangular_pattern.py
Modulo vocale: Serie Rettangolare Lineare (RectangularPatternFeatures.Add).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    conteggio_x = 3
    spaziatura_x_mm = 20.0
    conteggio_y = 2
    spaziatura_y_mm = 15.0

    match_cnt = re.search(r'(\d+)\s*(?:copie|elementi|colonne|x)\s*(\d+)?', f)
    if match_cnt:
        conteggio_x = int(match_cnt.group(1))
        if match_cnt.group(2):
            conteggio_y = int(match_cnt.group(2))

    match_spaz = re.search(r'(?:passo|spaziatura|distanza)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_spaz:
        spaziatura_x_mm = float(match_spaz.group(1).replace(',', '.'))

    return {
        "conteggio_x": conteggio_x,
        "spaziatura_x_mm": spaziatura_x_mm,
        "conteggio_y": conteggio_y,
        "spaziatura_y_mm": spaziatura_y_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spaz_x_cm = mm_to_cm(params["spaziatura_x_mm"])
    spaz_y_cm = mm_to_cm(params["spaziatura_y_mm"])

    resoconto = {
        "modulo": "RectangularPatternFeatures",
        "metodo": "RectangularPatternFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "spaz_x_cm": spaz_x_cm,
        "spaz_y_cm": spaz_y_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio_x"] > 1 and spaz_x_cm > 0
        assert abs(spaz_x_cm - params["spaziatura_x_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: RectangularPatternFeatures.Add {params['conteggio_x']}x{params['conteggio_y']} passo={spaz_x_cm} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_RectangularPattern")
    try:
        cd = part_doc.ComponentDefinition
        # Crea corpo base e foro se non esistono
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 120.0, 80.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)

        x_axis = cd.WorkAxes.Item(1)
        y_axis = cd.WorkAxes.Item(2)

        pattern = cd.Features.RectangularPatternFeatures.Add(
            feat_coll,
            x_axis,
            True,
            params["conteggio_x"],
            spaz_x_cm,
            20737, # kDefault
            y_axis,
            True,
            params["conteggio_y"],
            spaz_y_cm
        )
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Serie rettangolare creata: {pattern.Name}, Copie={params['conteggio_x']}x{params['conteggio_y']}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
