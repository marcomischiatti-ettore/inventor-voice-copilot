"""
comandi/hole_drilled_distance.py
Modulo vocale: Foro Cieco Semplice a Distanza (HoleFeatures.AddDrilledByDistanceExtent).
Supporta:
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

    # Fondo piatto o conico
    fondo_piatto = any(k in f for k in ["fondo piatto", "fondo piano", "piatto"])

    # Angolo di punta
    angolo_punta_deg = 118.0
    match_punta = re.search(r'punta\s*(?:a\s*)?(\d+(?:[.,]\d+)?)(?:\s*(?:gradi|°))?', f)
    if match_punta:
        angolo_punta_deg = float(match_punta.group(1).replace(',', '.'))

    # Profondità foro
    profondita_mm = 20.0
    patterns_prof = [
        r'(?:profondit[àa]|profondo|cieco|lunghezza)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?',
        r'(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)\s*(?:di\s+profondit[àa]|in\s+profondit[àa])'
    ]
    for pat in patterns_prof:
        m = re.search(pat, f)
        if m:
            val = float(m.group(1).replace(',', '.'))
            if abs(val - diametro_mm) > 1e-4 and abs(val - angolo_punta_deg) > 1e-4:
                profondita_mm = val
                break

    pos_info = analizza_posizionamento_foro(frase)

    res = {
        "diametro_mm": diametro_mm,
        "profondita_mm": profondita_mm,
        "fondo_piatto": fondo_piatto,
        "angolo_punta_deg": angolo_punta_deg,
        "frase_originale": frase
    }
    res.update(pos_info)
    return res


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    diametro_cm = mm_to_cm(params["diametro_mm"])
    profondita_cm = mm_to_cm(params["profondita_mm"])
    angolo_punta_rad = deg_to_rad(params["angolo_punta_deg"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddDrilledByDistanceExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "diametro_cm_inventor": diametro_cm,
        "profondita_cm_inventor": profondita_cm,
        "angolo_punta_rad": angolo_punta_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert diametro_cm > 0 and profondita_cm > 0
        assert abs(diametro_cm - (params["diametro_mm"] / 10.0)) < 1e-9
        assert abs(profondita_cm - (params["profondita_mm"] / 10.0)) < 1e-9
        resoconto["successo"] = True
        pos_desc = "al centro"
        if params.get("bordo1") and params.get("distanza1_mm") is not None:
            pos_desc = f"da {params['bordo1']}={params['distanza1_mm']}mm, {params['bordo2']}={params['distanza2_mm']}mm"
        elif not params.get("al_centro"):
            pos_desc = f"X={params['pos_x_mm']}mm, Y={params['pos_y_mm']}mm"
        resoconto["dettagli"] = f"Simulazione superata: AddDrilledByDistanceExtent D={diametro_cm:.4f} cm, H={profondita_cm:.4f} cm, Pos: {pos_desc}"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Autodesk Inventor.")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleDrilledDistance")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(40.0), kPositiveExtentDirection, kJoinOperation)

        place_def, pos_msg = create_smart_hole_placement(inv_app, part_doc, params)
        hole_feat = cd.Features.HoleFeatures.AddDrilledByDistanceExtent(
            place_def,
            diametro_cm,
            profondita_cm,
            kPositiveExtentDirection,
            params["fondo_piatto"],
            angolo_punta_rad
        )

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro cieco creato con successo: {hole_feat.Name}, D={params['diametro_mm']} mm, Prof={params['profondita_mm']} mm. {pos_msg}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e


esegui_foro_cieco = esegui_comando
