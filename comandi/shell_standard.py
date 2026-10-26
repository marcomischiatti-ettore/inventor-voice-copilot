"""
comandi/shell_standard.py
Modulo vocale: Svuotamento Solido con Spessore Parete (ShellFeatures.Add).
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
    spessore_mm = 2.0
    match_s = re.search(r'(?:spessore|parete|svuota)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_s:
        spessore_mm = float(match_s.group(1).replace(',', '.'))

    return {
        "spessore_mm": spessore_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spessore_cm = mm_to_cm(params["spessore_mm"])

    resoconto = {
        "modulo": "ShellFeatures",
        "metodo": "ShellFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "spessore_cm_inventor": spessore_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert spessore_cm > 0
        assert abs(spessore_cm - params["spessore_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: ShellFeatures.Add spessore={spessore_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ShellStandard")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(40.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        open_faces = inv_app.TransientObjects.CreateFaceCollection()
        # Rimuove la faccia superiore aperta
        for i in range(1, body.Faces.Count + 1):
            fc = body.Faces.Item(i)
            if hasattr(fc.Geometry, 'Normal') and abs(fc.Geometry.Normal.Z - 1.0) < 0.1:
                open_faces.Add(fc)
                break
        if open_faces.Count == 0:
            open_faces.Add(body.Faces.Item(1))

        shell_feat = cd.Features.ShellFeatures.Add(open_faces, spessore_cm, 20481) # Inside direction
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Svuotamento creato con successo: {shell_feat.Name}, Spessore={params['spessore_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
