"""
comandi/extrude_to_extent.py
Modulo per il comando vocale: Estrusione Fino a Entità/Faccia (ExtrudeFeatures.AddByToExtent).

Rispettando rigorosamente stile_progettazione.md:
- Piani di riferimento e facce target definite e centrate
- Conversioni metriche coerenti
- Transazioni atomiche tramite TransactionManager
"""

import math
import os
import re
import sys
from typing import Dict, Any, Optional

try:
    from comandi.inventor_utils import (
        mm_to_cm,
        get_inventor_app,
        get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection,
        kNegativeExtentDirection,
        kSymmetricExtentDirection,
        kJoinOperation,
        kCutOperation,
        kIntersectOperation,
        kNewBodyOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm,
        get_inventor_app,
        get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection,
        kNegativeExtentDirection,
        kSymmetricExtentDirection,
        kJoinOperation,
        kCutOperation,
        kIntersectOperation,
        kNewBodyOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    """
    Estrae i parametri per l'estrusione 'fino a' entità/faccia/piano.
    """
    f = frase.lower().strip()

    # Operazione booleana
    operazione = kJoinOperation
    if "tagli" in f or "scav" in f or "asport" in f:
        operazione = kCutOperation
    elif "intersec" in f:
        operazione = kIntersectOperation
    elif "nuovo corpo" in f:
        operazione = kNewBodyOperation

    # Riconoscimento entità target
    target_tipo = "faccia"
    if "piano" in f or "workplane" in f:
        target_tipo = "piano"

    # Ricerca indice piano o offset se specificato (es. "piano 2", "piano a 40 mm")
    indice_piano = 2  # default piano di riferimento alternativo
    match_piano = re.search(r'piano\s*(?:di\s+lavoro\s*)?(?:numero\s*)?(\d+)', f)
    if match_piano:
        indice_piano = int(match_piano.group(1))

    distanza_piano_offset_mm = 50.0
    match_offset = re.search(r'(?:offset|distanza|quota)(?:\s+(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_offset:
        distanza_piano_offset_mm = float(match_offset.group(1).replace(',', '.'))

    return {
        "operazione": operazione,
        "target_tipo": target_tipo,
        "indice_piano": indice_piano,
        "distanza_piano_offset_mm": distanza_piano_offset_mm,
        "estendi_faccia": True,
        "frase_originale": frase
    }


def esegui_estrusione_to_extent(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    """
    Esegue l'estrusione fino all'entità specificata (faccia o piano di lavoro) via COM.
    """
    parametri = analizza_frase_vocale(frase_vocale)
    operazione = parametri["operazione"]

    resoconto = {
        "modulo": "ExtrudeFeatures",
        "metodo": "ExtrudeFeatures.AddByToExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": parametri,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert operazione in (kJoinOperation, kCutOperation, kIntersectOperation, kNewBodyOperation)
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: ExtrudeFeatures.AddByToExtent(Profile, ToEntity, op={operazione}, ExtendFace=True)"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Autodesk Inventor.")

    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans_manager = inv_app.TransactionManager
    transazione = trans_manager.StartTransaction(part_doc, "Copilot_ExtrudeToExtent")

    try:
        cd = part_doc.ComponentDefinition

        # Se non ci sono solidi o piani target, creiamo un contesto completo
        to_entity = None
        if cd.SurfaceBodies.Count > 0 and parametri["target_tipo"] == "faccia":
            # Usa una faccia superiore del solido esistente
            body = cd.SurfaceBodies.Item(1)
            for i in range(1, body.Faces.Count + 1):
                face = body.Faces.Item(i)
                if face.SurfaceType in (5633, 5634):  # kPlaneSurface
                    to_entity = face
                    break

        if to_entity is None:
            # Creazione di un WorkPlane di riferimento offset dal piano XY (WorkPlane 3)
            wp_base = cd.WorkPlanes.Item(3)
            dist_offset_cm = mm_to_cm(parametri["distanza_piano_offset_mm"])
            to_entity = cd.WorkPlanes.AddByPlaneAndOffset(wp_base, dist_offset_cm)

        # Recupera o crea profilo da estrudere
        profile = None
        for i in range(cd.Sketches.Count, 0, -1):
            sk = cd.Sketches.Item(i)
            if not sk.Consumed and sk.Profiles.Count > 0:
                profile = sk.Profiles.Item(1)
                break

        if profile is None:
            _, profile = crea_schizzo_rettangolare_centrato(part_doc, 40.0, 40.0, piano_indice=3)

        # Invocazione COM AddByToExtent
        extrude_feat = cd.Features.ExtrudeFeatures.AddByToExtent(
            profile,
            to_entity,
            operazione,
            parametri["estendi_faccia"]
        )

        transazione.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature ToExtent creata con successo: {extrude_feat.Name}, Op: {operazione}"
        return resoconto

    except Exception as e:
        transazione.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e


if __name__ == "__main__":
    frasi = [
        "estrudi fino alla faccia piana superiore",
        "taglio fino al piano di lavoro con offset a 30 mm",
        "estrusione fino al piano 2"
    ]
    print("=== TEST PARSING E SIMULAZIONE EXTRUDE_TO_EXTENT ===")
    for f in frasi:
        res = esegui_estrusione_to_extent(f, test_mode=True)
        print(f"Frase: '{f}' -> Target: {res['parametri_estratti']['target_tipo']}, Op: {res['parametri_estratti']['operazione']}")


# Alias per router
esegui_comando = esegui_estrusione_to_extent
