"""
comandi/hole_definition.py
Modulo vocale per Fori Filettati / Maschiati avanzati (HoleFeatures con TapInfo).
Regole utente:
1. Se non specificato, il foro è SEMPRE passante e con filettatura per tutta la lunghezza.
2. Posizionamento libero tramite coordinate X e Y (es. "x50 y 50") oppure al centro (0, 0).
3. Direzione verso l'interno del solido (kPositiveExtentDirection).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )

# Tabella passi metrici standard ISO (passo grosso)
PASSI_METRICI_STANDARD = {
    3: "M3x0.5",
    4: "M4x0.7",
    5: "M5x0.8",
    6: "M6x1",
    8: "M8x1.25",
    10: "M10x1.5",
    12: "M12x1.75",
    14: "M14x2",
    16: "M16x2",
    18: "M18x2.5",
    20: "M20x2.5",
    24: "M24x3"
}


def ricava_designazione_metrica(testo: str, diametro_default: float) -> str:
    """Estrae o ricava la designazione metrica standard ISO (es. M10x1.5)."""
    m_full = re.search(r'\b(m\d+(?:[xX]\d+(?:[.,]\d+)?))\b', testo)
    if m_full:
        return m_full.group(1).upper().replace(',', '.')

    m_simple = re.search(r'\bm(\d+)\b', testo)
    if m_simple:
        d_val = int(m_simple.group(1))
        return PASSI_METRICI_STANDARD.get(d_val, f"M{d_val}x1.5")

    d_int = int(round(diametro_default))
    return PASSI_METRICI_STANDARD.get(d_int, f"M{d_int}x1.5")


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = 10.0
    profondita_mm = 20.0

    # 1. Regola: Se non specificato, il foro è SEMPRE passante
    # Diventa cieco solo se esplicitamente detto 'cieco' o se c'è una profondità indicata
    ha_profondita = False
    cieco = "cieco" in f

    match_prof = re.search(r'(?:profondit[àa]|profondo|lunghezza|prof)\s*[:=]?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if match_prof:
        profondita_mm = float(match_prof.group(1).replace(',', '.'))
        ha_profondita = True

    passante = not (cieco or ha_profondita)
    filettato = True
    filettatura_completa = True  # Regola: filettatura di tutto il foro sempre

    # 2. Diametro / Misura metrica (es. M16, M10, D16, ecc.)
    match_m = re.search(r'\bm(\d+(?:[xX]\d+(?:[.,]\d+)?)?)\b', f)
    if match_m:
        val_str = match_m.group(1).split('x')[0].split('X')[0]
        try:
            diametro_mm = float(val_str)
        except ValueError:
            diametro_mm = 10.0
    else:
        match_d = re.search(r'(?:diametro|d|foro)(?:\s*(?:di|a))?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
        if match_d:
            diametro_mm = float(match_d.group(1).replace(',', '.'))

    designazione = ricava_designazione_metrica(f, diametro_mm)

    # 3. Coordinate X e Y del foro (es. "x50 y 50", "x50 y50", "x: 50 y: 50")
    pos_x_mm = 0.0
    pos_y_mm = 0.0
    is_center = ("centro" in f or "centrat" in f)

    match_x = re.search(r'\bx\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)
    match_y = re.search(r'\by\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)

    if match_x:
        pos_x_mm = float(match_x.group(1).replace(',', '.'))
    if match_y:
        pos_y_mm = float(match_y.group(1).replace(',', '.'))

    return {
        "diametro_mm": diametro_mm,
        "profondita_mm": profondita_mm,
        "passante": passante,
        "filettato": filettato,
        "designazione": designazione,
        "filettatura_completa": filettatura_completa,
        "pos_x_mm": pos_x_mm,
        "pos_y_mm": pos_y_mm,
        "is_center": is_center and not (match_x or match_y),
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_mm"])
    h_cm = mm_to_cm(params["profondita_mm"])
    designazione = params["designazione"]
    pos_x_cm = mm_to_cm(params["pos_x_mm"])
    pos_y_cm = mm_to_cm(params["pos_y_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures con TapInfo (Foro Filettato)",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "h_cm": h_cm,
        "pos_x_cm": pos_x_cm,
        "pos_y_cm": pos_y_cm,
        "designazione": designazione,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0
        assert abs(d_cm - params["diametro_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = (
            f"Simulazione superata: Foro Filettato {designazione}, "
            f"Passante={params['passante']}, Pos=({params['pos_x_mm']}, {params['pos_y_mm']}) mm"
        )
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Autodesk Inventor.")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=True)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleTapped")
    try:
        cd = part_doc.ComponentDefinition
        # Se non esiste un solido, crea una piastra base centrata
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 200.0, 100.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(20.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        # Trova la faccia piana superiore (normale parallela all'asse Z)
        target_face = None
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, 'Normal') and abs(f.Geometry.Normal.Z - 1.0) < 0.1:
                target_face = f
                break
        if target_face is None:
            target_face = body.Faces.Item(1)

        # Crea schizzo sulla faccia per lo SketchPoint
        sk = cd.Sketches.Add(target_face)
        tg = inv_app.TransientGeometry
        
        # Posiziona lo SketchPoint alle coordinate esatte fornite dall'utente (in cm)
        sp = sk.SketchPoints.Add(tg.CreatePoint2d(pos_x_cm, pos_y_cm))

        # Se il foro è al centro e non sono state fornite coordinate diverse, vincola all'origine
        if params["is_center"] or (abs(pos_x_cm) < 1e-6 and abs(pos_y_cm) < 1e-6 and not ("x" in frase_vocale.lower() or "y" in frase_vocale.lower())):
            try:
                proj_origin = sk.AddByProjectingEntity(cd.WorkPoints.Item(1))
                sk.GeometricConstraints.AddCoincident(sp, proj_origin)
            except Exception:
                pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        place_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(coll)

        # 1. Creazione della foratura (Passante di default, o Cieca se specificato)
        # Direzione: kPositiveExtentDirection (verso l'interno del pezzo)
        if params["passante"]:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByThroughAllExtent(
                place_def, d_cm, kPositiveExtentDirection
            )
        else:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByDistanceExtent(
                place_def, d_cm, h_cm, kPositiveExtentDirection, False, deg_to_rad(118.0)
            )

        # 2. Creazione TapInfo con filettatura per tutta la lunghezza (FullTapDepth = True)
        tapped_ok = False
        try:
            ti = cd.Features.HoleFeatures.CreateTapInfo(
                True,                   # Filettatura destrorsa standard
                "ISO Metric profile",   # Profilo metrico ISO
                designazione,           # es. M16x2, M10x1.5
                "6H",                   # Tolleranza madrevite
                True                    # Tutta la lunghezza sempre attiva
            )
            hole_feat.TapInfo = ti
            tapped_ok = hole_feat.Tapped
        except Exception:
            try:
                ti = cd.Features.HoleFeatures.CreateTapInfo(
                    True, "ISO Metric profile", designazione, "6H", False, h_cm
                )
                hole_feat.TapInfo = ti
                tapped_ok = hole_feat.Tapped
            except Exception:
                pass

        trans.End()
        resoconto["successo"] = True
        tipo_str = "Passante" if params["passante"] else f"Cieco ({params['profondita_mm']} mm)"
        status_filetto = f"Filettato ({designazione})" if tapped_ok else f"Base ({designazione})"
        resoconto["dettagli"] = (
            f"Foro {status_filetto} {tipo_str} creato con successo: {hole_feat.Name} "
            f"in Posizione X={params['pos_x_mm']} mm, Y={params['pos_y_mm']} mm"
        )
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
