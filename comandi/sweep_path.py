"""
comandi/sweep_path.py
Modulo vocale: Sweep Lungo Percorso/Traiettoria (SweepFeatures.AddUsingPath).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_sezione_mm = 8.0
    match_d = re.search(r'(?:sezione|diametro|profilo)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_sezione_mm = float(match_d.group(1).replace(',', '.'))

    lunghezza_percorso_mm = 60.0
    match_l = re.search(r'(?:lunghezza|percorso|corsa)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_l:
        lunghezza_percorso_mm = float(match_l.group(1).replace(',', '.'))

    return {
        "diametro_sezione_mm": diametro_sezione_mm,
        "lunghezza_percorso_mm": lunghezza_percorso_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_sezione_mm"])
    l_cm = mm_to_cm(params["lunghezza_percorso_mm"])

    resoconto = {
        "modulo": "SweepFeatures",
        "metodo": "SweepFeatures.AddUsingPath",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "l_cm": l_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0 and l_cm > 0
        assert abs(d_cm - params["diametro_sezione_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: SweepFeatures.AddUsingPath D={d_cm:.4f} cm, L={l_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_SweepPath")
    try:
        cd = part_doc.ComponentDefinition
        # Profilo su XY Plane (WorkPlane 3)
        _, profile = crea_schizzo_circolare_centrato(part_doc, params["diametro_sezione_mm"], 3)

        # Percorso su XZ Plane (WorkPlane 2) ortogonale
        wp_path = cd.WorkPlanes.Item(2)
        sk_path = cd.Sketches.Add(wp_path)
        tg = inv_app.TransientGeometry
        p_start = tg.CreatePoint2d(0, 0)
        p_end = tg.CreatePoint2d(0, l_cm)
        path_line = sk_path.SketchLines.AddByTwoPoints(p_start, p_end)
        path = cd.Features.SweepFeatures.CreatePath(path_line)

        sweep_feat = cd.Features.SweepFeatures.AddUsingPath(profile, path, kJoinOperation)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Sweep creato con successo: {sweep_feat.Name}, Sezione={params['diametro_sezione_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
