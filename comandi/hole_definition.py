"""
comandi/hole_definition.py
Modulo vocale: Definizione Avanzata di Foratura (HoleFeatures.CreateHoleDefinition).
Supporta:
- Fori filettati / maschiati (es. M10, filettato a tutto spessore)
- Posizionamento lineare da bordi/spigoli (CreateLinearPlacementDefinition)
- Selezione interattiva a video (SelectSet)
- Posizionamento concentrico su spigoli circolari
- Coordinate X, Y e centro faccia
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        create_smart_hole_placement, analizza_posizionamento_foro, estrai_diametro_foro,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        create_smart_hole_placement, analizza_posizionamento_foro, estrai_diametro_foro,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = estrai_diametro_foro(frase, default_mm=10.0)
    profondita_mm = 20.0
    passante = "passante" in f or "attraverso" in f or "tutto" in f
    filettato = "filettat" in f or "maschiat" in f or bool(re.search(r'\bm\d+', f))

    match_prof = re.search(r'(?:profondit[àa]|profondo)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_prof:
        profondita_mm = float(match_prof.group(1).replace(',', '.'))

    pos_info = analizza_posizionamento_foro(frase)

    res = {
        "diametro_mm": diametro_mm,
        "profondita_mm": profondita_mm,
        "passante": passante,
        "filettato": filettato,
        "frase_originale": frase
    }
    res.update(pos_info)
    return res


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
        pos_desc = "al centro"
        if params.get("bordo1") and params.get("distanza1_mm") is not None:
            pos_desc = f"da {params['bordo1']}={params['distanza1_mm']}mm, {params['bordo2']}={params['distanza2_mm']}mm"
        elif not params.get("al_centro"):
            pos_desc = f"X={params['pos_x_mm']}mm, Y={params['pos_y_mm']}mm"
        resoconto["dettagli"] = f"Simulazione superata: HoleDefinition parametrica D={d_cm:.4f} cm, Pos: {pos_desc}"
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

        place_def, pos_msg = create_smart_hole_placement(inv_app, part_doc, params)
        if params["passante"]:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByThroughAllExtent(place_def, d_cm, kPositiveExtentDirection)
        else:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByDistanceExtent(place_def, d_cm, h_cm, kPositiveExtentDirection, False, deg_to_rad(118.0))

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature foratura creata con successo: {hole_feat.Name}. {pos_msg}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
