"""
comandi/hole_drilled_through_all.py
Modulo vocale: Foro Passante Semplice (HoleFeatures.AddDrilledByThroughAllExtent).
Supporta:
- Posizionamento lineare da bordi/spigoli con quote parametriche visibili
- Selezione interattiva a video (SelectSet)
- Posizionamento concentrico su spigoli circolari
- Coordinate X, Y e centro faccia
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        create_smart_hole_placement, analizza_posizionamento_foro, estrai_diametro_foro,
        kPositiveExtentDirection, kNegativeExtentDirection, kSymmetricExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        create_smart_hole_placement, analizza_posizionamento_foro, estrai_diametro_foro,
        kPositiveExtentDirection, kNegativeExtentDirection, kSymmetricExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = estrai_diametro_foro(frase, default_mm=10.0)

    # Direzione foratura verso il solido (in Inventor kPositiveExtentDirection è la normale entrante)
    direzione = kPositiveExtentDirection
    if "entrambi" in f or "simmetric" in f:
        direzione = kSymmetricExtentDirection

    pos_info = analizza_posizionamento_foro(frase)

    res = {
        "diametro_mm": diametro_mm,
        "direzione": direzione,
        "frase_originale": frase
    }
    res.update(pos_info)
    return res


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
        pos_desc = "al centro"
        if params.get("bordo1") and params.get("distanza1_mm") is not None:
            pos_desc = f"da {params['bordo1']}={params['distanza1_mm']}mm, {params['bordo2']}={params['distanza2_mm']}mm"
        elif not params.get("al_centro"):
            pos_desc = f"X={params['pos_x_mm']}mm, Y={params['pos_y_mm']}mm"
        resoconto["dettagli"] = f"Simulazione superata: AddDrilledByThroughAllExtent D={diametro_cm:.4f} cm, Pos: {pos_desc}"
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

        place_def, pos_msg = create_smart_hole_placement(inv_app, part_doc, params)
        hole_feat = cd.Features.HoleFeatures.AddDrilledByThroughAllExtent(place_def, diametro_cm, params["direzione"])

        trans.End()
        try:
            part_doc.Update2(True)
        except Exception:
            try:
                part_doc.Update()
            except Exception:
                pass

        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro passante creato con successo: {hole_feat.Name}, D={params['diametro_mm']} mm. {pos_msg}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
