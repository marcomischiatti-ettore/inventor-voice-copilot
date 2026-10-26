"""
comandi/hole_drilled_distance.py
Modulo per il comando vocale: Foro Cieco Semplice a Distanza (HoleFeatures.AddDrilledByDistanceExtent).

Rispettando rigorosamente stile_progettazione.md:
- Conversione metrica millimetri -> centimetri (mm / 10.0) per diametro e profondità
- Conversione angolare in radianti per angolo di punta (TipAngle)
- Posizionamento su SketchPoint vincolato e centrato sull'origine (0, 0)
- Incapsulamento in CreateSketchPlacementDefinition conforme alle API COM di Inventor
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
        deg_to_rad,
        get_inventor_app,
        get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection,
        kPositiveExtentDirection,
        kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm,
        deg_to_rad,
        get_inventor_app,
        get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection,
        kPositiveExtentDirection,
        kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    """
    Estrae diametro, profondità, tipo di fondo (piatto o conico), ed eventuali coordinate del foro.
    """
    f = frase.lower().strip()

    # 1. Fondo piatto o conico
    fondo_piatto = False
    if "fondo piatto" in f or "fondo piano" in f or "piatto" in f:
        fondo_piatto = True

    # 2. Angolo di punta (standard per punte da trapano è 118 gradi)
    angolo_punta_deg = 118.0
    match_punta = re.search(r'punta\s*(?:a\s*)?(\d+(?:[.,]\d+)?)(?:\s*(?:gradi|°))?', f)
    if match_punta:
        angolo_punta_deg = float(match_punta.group(1).replace(',', '.'))

    # 3. Diametro foro (mm)
    diametro_mm = 10.0
    patterns_diametro = [
        r'(?:diametro|d|foro)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?',
        r'(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)\s*(?:di\s+diametro)'
    ]
    for pat in patterns_diametro:
        m = re.search(pat, f)
        if m:
            diametro_mm = float(m.group(1).replace(',', '.'))
            break

    # 4. Profondità foro (mm)
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

    # 5. Coordinate centro foro (default centrato su origine 0, 0)
    pos_x_mm = 0.0
    pos_y_mm = 0.0
    match_x = re.search(r'\bx\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)
    match_y = re.search(r'\by\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)
    if match_x:
        pos_x_mm = float(match_x.group(1).replace(',', '.'))
    if match_y:
        pos_y_mm = float(match_y.group(1).replace(',', '.'))

    return {
        "diametro_mm": diametro_mm,
        "profondita_mm": profondita_mm,
        "fondo_piatto": fondo_piatto,
        "angolo_punta_deg": angolo_punta_deg,
        "pos_x_mm": pos_x_mm,
        "pos_y_mm": pos_y_mm,
        "frase_originale": frase
    }


def esegui_foro_cieco(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    """
    Esegue la creazione di un foro cieco semplice a distanza tramite HoleFeatures.AddDrilledByDistanceExtent.
    """
    parametri = analizza_frase_vocale(frase_vocale)
    diametro_mm = parametri["diametro_mm"]
    profondita_mm = parametri["profondita_mm"]
    fondo_piatto = parametri["fondo_piatto"]
    angolo_punta_deg = parametri["angolo_punta_deg"]

    diametro_cm = mm_to_cm(diametro_mm)
    profondita_cm = mm_to_cm(profondita_mm)
    angolo_punta_rad = deg_to_rad(angolo_punta_deg)

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddDrilledByDistanceExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": parametri,
        "diametro_cm_inventor": diametro_cm,
        "profondita_cm_inventor": profondita_cm,
        "angolo_punta_rad": angolo_punta_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert diametro_cm > 0, "Diametro foro deve essere strettamente positivo"
        assert profondita_cm > 0, "Profondita foro deve essere strettamente positiva"
        assert abs(diametro_cm - (diametro_mm / 10.0)) < 1e-9, "Errore conversione metrica diametro: mm/10 != cm"
        assert abs(profondita_cm - (profondita_mm / 10.0)) < 1e-9, "Errore conversione metrica profondita: mm/10 != cm"
        resoconto["successo"] = True
        resoconto["dettagli"] = (
            f"Simulazione superata: AddDrilledByDistanceExtent(D={diametro_cm:.4f} cm, H={profondita_cm:.4f} cm, "
            f"Flat={fondo_piatto}, TipAngle={angolo_punta_rad:.4f} rad)"
        )
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Autodesk Inventor.")

    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans_manager = inv_app.TransactionManager
    transazione = trans_manager.StartTransaction(part_doc, "Copilot_HoleDrilledDistance")

    try:
        cd = part_doc.ComponentDefinition

        # Se non esiste un solido, crea un blocco base centrato
        if cd.SurfaceBodies.Count == 0:
            _, base_profile = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, piano_indice=3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(
                base_profile,
                mm_to_cm(40.0),
                kPositiveExtentDirection,
                kJoinOperation
            )

        # Individua la faccia piana superiore (normale parallela all'asse Z)
        target_face = None
        body = cd.SurfaceBodies.Item(1)
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, 'Normal') and abs(f.Geometry.Normal.Z - 1.0) < 0.1:
                target_face = f
                break

        if target_face is None:
            target_face = body.Faces.Item(1)

        # Crea schizzo sulla faccia e aggiunge lo SketchPoint per il foro
        hole_sketch = cd.Sketches.Add(target_face)
        tg = inv_app.TransientGeometry

        pos_x_cm = mm_to_cm(parametri["pos_x_mm"])
        pos_y_cm = mm_to_cm(parametri["pos_y_mm"])
        pt2d = tg.CreatePoint2d(pos_x_cm, pos_y_cm)
        sketch_point = hole_sketch.SketchPoints.Add(pt2d)

        # Se il foro è al centro (0, 0), aggiunge vincolo di coincidenza con l'origine
        if abs(pos_x_cm) < 1e-6 and abs(pos_y_cm) < 1e-6:
            try:
                hole_sketch.GeometricConstraints.AddCoincident(hole_sketch.OriginPoint, sketch_point)
            except Exception:
                pass

        # Creazione del PlacementDefinition tramite CreateSketchPlacementDefinition
        points_coll = inv_app.TransientObjects.CreateObjectCollection()
        points_coll.Add(sketch_point)
        placement_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(points_coll)

        # Invocazione COM AddDrilledByDistanceExtent
        hole_feat = cd.Features.HoleFeatures.AddDrilledByDistanceExtent(
            placement_def,
            diametro_cm,
            profondita_cm,
            kPositiveExtentDirection,
            fondo_piatto,
            angolo_punta_rad
        )

        transazione.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro creato con successo: {hole_feat.Name}, D={diametro_mm} mm, Prof={profondita_mm} mm"
        return resoconto

    except Exception as e:
        transazione.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e


if __name__ == "__main__":
    frasi = [
        "foro cieco diametro 10 profondita 25 mm al centro",
        "crea un foro di 12 mm profondo 30 mm con fondo piatto",
        "foratura diametro 8 profondita 15 mm punta a 118 gradi"
    ]
    print("=== TEST PARSING E SIMULAZIONE HOLE_DRILLED_DISTANCE ===")
    for f in frasi:
        res = esegui_foro_cieco(f, test_mode=True)
        print(f"Frase: '{f}' -> D: {res['diametro_cm_inventor']} cm, H: {res['profondita_cm_inventor']} cm, Piatto: {res['parametri_estratti']['fondo_piatto']}")


# Alias per router
esegui_comando = esegui_foro_cieco
