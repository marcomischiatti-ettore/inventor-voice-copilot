"""
comandi/hole_csink_distance.py
Modulo vocale: Foro Svasato a Distanza (HoleFeatures.AddCSinkByDistanceExtent).
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
    diametro_mm = estrai_diametro_foro(frase, default_mm=6.0)
    csink_diametro_mm = max(12.0, diametro_mm * 1.8)
    csink_angolo_deg = 90.0
    profondita_mm = 20.0

    match_csd = re.search(r'(?:svasatura|csink|svaso)(?:\s*(?:di|a|diametro))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_csd:
        csink_diametro_mm = float(match_csd.group(1).replace(',', '.'))

    match_ang = re.search(r'(?:angolo\s+svaso|angolo\s+svasatura|svasatura\s+a)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:gradi|°))?', f)
    if match_ang:
        csink_angolo_deg = float(match_ang.group(1).replace(',', '.'))

    match_prof = re.search(r'(?:profondit[àa]|profondo|cieco)(?:\s*(?:totale|di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_prof:
        val = float(match_prof.group(1).replace(',', '.'))
        if abs(val - csink_diametro_mm) > 1e-3 and abs(val - diametro_mm) > 1e-3:
            profondita_mm = val

    pos_info = analizza_posizionamento_foro(frase)

    res = {
        "diametro_mm": diametro_mm,
        "csink_diametro_mm": csink_diametro_mm,
        "csink_angolo_deg": csink_angolo_deg,
        "profondita_mm": profondita_mm,
        "frase_originale": frase
    }
    res.update(pos_info)
    return res


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_mm"])
    csd_cm = mm_to_cm(params["csink_diametro_mm"])
    csa_rad = deg_to_rad(params["csink_angolo_deg"])
    h_cm = mm_to_cm(params["profondita_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddCSinkByDistanceExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "csink_d_cm": csd_cm,
        "csink_a_rad": csa_rad,
        "h_cm": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0 and csd_cm > d_cm and csa_rad > 0 and h_cm > 0
        assert abs(d_cm - params["diametro_mm"]/10.0) < 1e-9
        assert abs(csa_rad - math.radians(params["csink_angolo_deg"])) < 1e-9
        resoconto["successo"] = True
        pos_desc = "al centro"
        if params.get("bordo1") and params.get("distanza1_mm") is not None:
            pos_desc = f"da {params['bordo1']}={params['distanza1_mm']}mm, {params['bordo2']}={params['distanza2_mm']}mm"
        elif not params.get("al_centro"):
            pos_desc = f"X={params['pos_x_mm']}mm, Y={params['pos_y_mm']}mm"
        resoconto["dettagli"] = f"Simulazione superata: AddCSinkByDistanceExtent D={d_cm}cm, CSinkAngle={csa_rad}rad, Pos: {pos_desc}"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleCSinkDistance")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(50.0), kPositiveExtentDirection, kJoinOperation)

        place_def, pos_msg = create_smart_hole_placement(inv_app, part_doc, params)
        hole_feat = cd.Features.HoleFeatures.AddCSinkByDistanceExtent(
            place_def, d_cm, csd_cm, csa_rad, h_cm, kPositiveExtentDirection, False, deg_to_rad(118.0)
        )

        trans.End()
        try:
            part_doc.Update2(True)
        except Exception:
            try:
                part_doc.Update()
            except Exception:
                pass
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro svasato creato con successo: {hole_feat.Name}, D={params['diametro_mm']}mm, Angolo={params['csink_angolo_deg']}°. {pos_msg}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
