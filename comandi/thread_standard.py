"""
comandi/thread_standard.py
Modulo vocale: Filettatura Standard su Faccia Cilindrica (ThreadFeatures.Add).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    designazione = "M10x1.5"
    match_m = re.search(r'(m\d+(?:x\d+(?:[.,]\d+)?)?)', f)
    if match_m:
        designazione = match_m.group(1).upper().replace(',', '.')

    lunghezza_totale = "tutta la lunghezza" in f or "completa" in f or "passante" in f
    lunghezza_filetto_mm = 20.0
    match_l = re.search(r'(?:lunghezza|profondit[àa])(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_l:
        lunghezza_filetto_mm = float(match_l.group(1).replace(',', '.'))

    return {
        "designazione": designazione,
        "lunghezza_totale": lunghezza_totale,
        "lunghezza_filetto_mm": lunghezza_filetto_mm,
        "destrorsa": "sinistrorsa" not in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    l_cm = mm_to_cm(params["lunghezza_filetto_mm"])

    resoconto = {
        "modulo": "ThreadFeatures",
        "metodo": "ThreadFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "lunghezza_cm_inventor": l_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert l_cm > 0
        assert abs(l_cm - params["lunghezza_filetto_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: ThreadFeatures.Add {params['designazione']} L={l_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ThreadStandard")
    try:
        cd = part_doc.ComponentDefinition
        cyl_face = None
        if cd.SurfaceBodies.Count > 0:
            body = cd.SurfaceBodies.Item(1)
            for i in range(1, body.Faces.Count + 1):
                fc = body.Faces.Item(i)
                if fc.SurfaceType in (5635, 5636):
                    cyl_face = fc
                    break

        if cyl_face is None:
            _, sk_circ = crea_schizzo_circolare_centrato(part_doc, 10.0, 3)
            ext_cyl = cd.Features.ExtrudeFeatures.AddByDistanceExtent(sk_circ, mm_to_cm(35.0), kPositiveExtentDirection, kJoinOperation)
            for i in range(1, ext_cyl.Faces.Count + 1):
                fc = ext_cyl.Faces.Item(i)
                if fc.SurfaceType in (5635, 5636):
                    cyl_face = fc
                    break

        thread_info = cd.Features.ThreadFeatures.CreateStandardThreadInfo(
            params["lunghezza_totale"],
            params["destrorsa"],
            "ISO Metric profile",
            params["designazione"],
            "6g"
        )
        if not params["lunghezza_totale"]:
            thread_info.ThreadLength = l_cm

        thread_feat = cd.Features.ThreadFeatures.Add(cyl_face, thread_info)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Filettatura creata con successo: {thread_feat.Name}, Taglia: {params['designazione']}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
