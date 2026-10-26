"""
comandi/extrude_through_all.py
Modulo per il comando vocale: Estrusione Passante Totale (ExtrudeFeatures.AddByThroughAllExtent).

Rispettando rigorosamente stile_progettazione.md:
- Geometria e forometria centrate sull'origine
- Conversione metrica coerente (mm / 10.0) per profili associati
- Transazionalità atomica tramite TransactionManager
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
        crea_schizzo_circolare_centrato,
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
        crea_schizzo_circolare_centrato,
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
    Estrae i parametri per un'estrusione passante attraverso tutto.
    Default operazione: kCutOperation (taglio passante), tipico uso di ThroughAllExtent.
    """
    f = frase.lower().strip()

    # 1. Direzione dell'estensione passante
    direzione = kSymmetricExtentDirection  # Spesso passante da entrambi i lati o negativa attraverso il pezzo
    if "verso l'alto" in f or "positiv" in f or "in su" in f:
        direzione = kPositiveExtentDirection
    elif "verso il basso" in f or "negativ" in f or "in giu" in f or "in giù" in f:
        direzione = kNegativeExtentDirection
    elif "simmetric" in f or "entrambi" in f or "tutto" in f:
        direzione = kSymmetricExtentDirection

    # 2. Tipo di operazione
    # Se viene specificato "unione" o "aggiungi", usa kJoinOperation, altrimenti per difetto il passante è un taglio
    operazione = kCutOperation
    if "unisc" in f or "aggiung" in f or "solido passante" in f:
        operazione = kJoinOperation
    elif "intersec" in f:
        operazione = kIntersectOperation
    elif "nuovo corpo" in f:
        operazione = kNewBodyOperation

    # 3. Riconoscimento eventuale geometria profilo nel comando vocale
    # Es. "cava circolare diametro 20 passante", "asola 30 per 10 passante"
    diametro_foro_mm = None
    match_diametro = re.search(r'(?:diametro|d|foro|cerchio)\s*(?:di\s+)?(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_diametro:
        diametro_foro_mm = float(match_diametro.group(1).replace(',', '.'))

    larghezza_taglio_mm = None
    altezza_taglio_mm = None
    match_rett = re.search(r'(?:asola|apertura|tasca|cava)?\s*(\d+(?:[.,]\d+)?)\s*(?:per|x|\*)\s*(\d+(?:[.,]\d+)?)', f)
    if match_rett:
        larghezza_taglio_mm = float(match_rett.group(1).replace(',', '.'))
        altezza_taglio_mm = float(match_rett.group(2).replace(',', '.'))

    return {
        "direzione": direzione,
        "operazione": operazione,
        "diametro_foro_mm": diametro_foro_mm,
        "larghezza_taglio_mm": larghezza_taglio_mm,
        "altezza_taglio_mm": altezza_taglio_mm,
        "frase_originale": frase
    }


def esegui_estrusione_passante(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    """
    Esegue l'estrusione passante totale tramite le API COM di Autodesk Inventor.
    """
    parametri = analizza_frase_vocale(frase_vocale)
    direzione = parametri["direzione"]
    operazione = parametri["operazione"]

    resoconto = {
        "modulo": "ExtrudeFeatures",
        "metodo": "ExtrudeFeatures.AddByThroughAllExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": parametri,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert direzione in (kPositiveExtentDirection, kNegativeExtentDirection, kSymmetricExtentDirection)
        assert operazione in (kJoinOperation, kCutOperation, kIntersectOperation, kNewBodyOperation)
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: ExtrudeFeatures.AddByThroughAllExtent(Profile, dir={direzione}, op={operazione})"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Autodesk Inventor.")

    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans_manager = inv_app.TransactionManager
    transazione = trans_manager.StartTransaction(part_doc, "Copilot_ExtrudeThroughAll")

    try:
        cd = part_doc.ComponentDefinition

        # Se non ci sono corpi solidi esistenti, creiamo un corpo base simmetrico
        if cd.SurfaceBodies.Count == 0:
            _, base_profile = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, piano_indice=3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(
                base_profile,
                mm_to_cm(30.0),
                kPositiveExtentDirection,
                kJoinOperation
            )

        # Recupera profilo esistente non consumato o creane uno centrato
        profile = None
        for i in range(cd.Sketches.Count, 0, -1):
            sk = cd.Sketches.Item(i)
            if not sk.Consumed and sk.Profiles.Count > 0:
                profile = sk.Profiles.Item(1)
                break

        if profile is None:
            # Creiamo un profilo di taglio centrato sull'origine del piano XY o su faccia piana
            if parametri["diametro_foro_mm"]:
                _, profile = crea_schizzo_circolare_centrato(part_doc, parametri["diametro_foro_mm"], piano_indice=3)
            elif parametri["larghezza_taglio_mm"] and parametri["altezza_taglio_mm"]:
                _, profile = crea_schizzo_rettangolare_centrato(
                    part_doc, parametri["larghezza_taglio_mm"], parametri["altezza_taglio_mm"], piano_indice=3
                )
            else:
                # Profilo di default centrato per taglio passante (es. apertura 20x20 mm)
                _, profile = crea_schizzo_rettangolare_centrato(part_doc, 20.0, 20.0, piano_indice=3)

        # Invocazione COM AddByThroughAllExtent
        extrude_feat = cd.Features.ExtrudeFeatures.AddByThroughAllExtent(
            profile,
            direzione,
            operazione
        )

        transazione.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature passante creata con successo: {extrude_feat.Name}, Dir: {direzione}, Op: {operazione}"
        return resoconto

    except Exception as e:
        transazione.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e


if __name__ == "__main__":
    frasi = [
        "taglio passante attraverso tutto il pezzo",
        "estrudi passante con apertura 30 per 15 mm",
        "fai un foro passante diametro 16 millimetri attraverso tutto",
        "estrusione passante simmetrica verso il basso"
    ]
    print("=== TEST PARSING E SIMULAZIONE EXTRUDE_THROUGH_ALL ===")
    for f in frasi:
        res = esegui_estrusione_passante(f, test_mode=True)
        print(f"Frase: '{f}' -> Dir: {res['parametri_estratti']['direzione']}, Op: {res['parametri_estratti']['operazione']}")


# Alias per router
esegui_comando = esegui_estrusione_passante
