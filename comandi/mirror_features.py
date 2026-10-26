"""
comandi/mirror_features.py
Modulo vocale: Specchiatura Feature su Piano di Simmetria (MirrorFeatures.Add).
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
    piano_indice = 1 # YZ plane (X=0)
    if "xz" in f or "piano 2" in f:
        piano_indice = 2
    elif "xy" in f or "piano 3" in f:
        piano_indice = 3

    return {
        "piano_indice": piano_indice,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)

    resoconto = {
        "modulo": "MirrorFeatures",
        "metodo": "MirrorFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["piano_indice"] in (1, 2, 3)
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: MirrorFeatures.Add su WorkPlane {params['piano_indice']}"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_MirrorFeatures")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        mirror_plane = cd.WorkPlanes.Item(params["piano_indice"])

        mirror_feat = cd.Features.MirrorFeatures.Add(feat_coll, mirror_plane)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature specchiata con successo: {mirror_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
