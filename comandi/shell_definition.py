"""
comandi/shell_definition.py
Modulo vocale: Definizione Avanzata Svuotamento (ShellFeatures.CreateShellDefinition).
Supporta:
- Selezione interattiva a video della faccia/facce da aprire (SelectSet)
- Selezione semantica da voce (faccia superiore, inferiore, frontale, destra, sinistra)
- Svuotamento a corpo chiuso senza rimuovere facce (solido cavo chiuso)
- Spessore parametrico convertito in cm per Inventor
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        get_active_selection, find_face_by_direction,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        get_active_selection, find_face_by_direction,
        kPositiveExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    spessore_mm = 2.5
    match_s = re.search(r'(?:spessore|parete|svuota|thk|s)(?:\s*(?:di|a|da))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_s:
        spessore_mm = float(match_s.group(1).replace(',', '.'))

    corpo_chiuso = any(k in f for k in ["corpo chiuso", "solido chiuso", "chiuso", "senza rimuovere", "senza aprire", "cavo"])

    faccia_target = None
    for orient in ["superiore", "inferiore", "frontale", "posteriore", "destra", "destro", "sinistra", "sinistro", "sopra", "sotto", "fondo", "alto", "basso"]:
        if orient in f:
            faccia_target = orient
            break

    return {
        "spessore_mm": spessore_mm,
        "corpo_chiuso": corpo_chiuso,
        "faccia_target": faccia_target,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spessore_cm = mm_to_cm(params["spessore_mm"])

    resoconto = {
        "modulo": "ShellFeatures",
        "metodo": "ShellFeatures.CreateShellDefinition",
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
        desc = "corpo chiuso" if params["corpo_chiuso"] else f"faccia: {params.get('faccia_target') or 'default superiore'}"
        resoconto["dettagli"] = f"Simulazione superata: CreateShellDefinition spessore={spessore_cm:.4f} cm ({desc})"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ShellDef")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(40.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        open_faces = inv_app.TransientObjects.CreateFaceCollection()
        faccia_desc = "corpo chiuso"

        if not params["corpo_chiuso"]:
            sel = get_active_selection(part_doc)
            if sel["faces"]:
                for fc in sel["faces"]:
                    open_faces.Add(fc)
                faccia_desc = f"{len(sel['faces'])} faccia/e selezionata/e rimossa/e"
            elif params.get("faccia_target"):
                target_fc = find_face_by_direction(body, params["faccia_target"])
                if target_fc:
                    open_faces.Add(target_fc)
                    faccia_desc = f"faccia {params['faccia_target']} rimossa"
            else:
                target_fc = find_face_by_direction(body, "top")
                if target_fc:
                    open_faces.Add(target_fc)
                    faccia_desc = "faccia superiore (+Z) rimossa"

        shell_def = cd.Features.ShellFeatures.CreateShellDefinition(open_faces, spessore_cm, 20481)
        shell_feat = cd.Features.ShellFeatures.AddByDefinition(shell_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione svuotamento creata con successo: {shell_feat.Name}, Spessore={params['spessore_mm']} mm ({faccia_desc})"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
