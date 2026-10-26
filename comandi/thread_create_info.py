"""
comandi/thread_create_info.py
Modulo vocale: Configurazione Informazioni Filettatura (ThreadFeatures.CreateThreadInfo).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    designazione = "M12x1.75"
    match_m = re.search(r'(m\d+(?:x\d+(?:[.,]\d+)?)?)', f)
    if match_m:
        designazione = match_m.group(1).upper().replace(',', '.')

    classe = "6g"
    match_cl = re.search(r'classe\s*([4-8][gh])', f)
    if match_cl:
        classe = match_cl.group(1)

    destrorsa = "sinistr" not in f
    full_length = "totale" in f or "tutto" in f

    return {
        "designazione": designazione,
        "classe": classe,
        "destrorsa": destrorsa,
        "full_length": full_length,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)

    resoconto = {
        "modulo": "ThreadFeatures",
        "metodo": "ThreadFeatures.CreateThreadInfo",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert len(params["designazione"]) > 0
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: Configurazione ThreadInfo {params['designazione']} cl={params['classe']}"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ThreadCreateInfo")
    try:
        cd = part_doc.ComponentDefinition
        info = cd.Features.ThreadFeatures.CreateStandardThreadInfo(
            params["full_length"],
            params["destrorsa"],
            "ISO Metric profile",
            params["designazione"],
            params["classe"]
        )
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"ThreadInfo configurato con successo: {info.ThreadDesignation}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
