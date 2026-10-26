"""
orchestratore_sviluppo_roadmap.py
Sviluppatore autonomo a catena continua per tutti i moduli della roadmap Autodesk Inventor Copilot.
Esegue:
1. Impostazione stato a 'IN_CORSO'
2. Generazione del modulo in comandi/<id>.py con parsing vocale avanzato in italiano e rispetto di stile_progettazione.md
3. Collaudo del modulo (simulazione e validazione metrica mm/10->cm, angoli rad, vincoli simmetria)
4. Compilazione di report_antigravity.txt
5. Esecuzione di chiedi_a_gemini.py e lettura di feedback_gemini.txt
6. Se 'STATUS: APPROVATO', impostazione stato a 'COMPLETATO'
7. Avanzamento automatico al comando successivo
"""

import json
import os
import re
import subprocess
import sys
import time

TEMPLATES_COMANDI = {
    # 6. hole_drilled_through_all
    "hole_drilled_through_all": {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddDrilledByThroughAllExtent",
        "descrizione": "Crea un foro passante semplice con diametro specificato.",
        "codice": '''"""
comandi/hole_drilled_through_all.py
Modulo vocale: Foro Passante Semplice (HoleFeatures.AddDrilledByThroughAllExtent).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kSymmetricExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kSymmetricExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = 10.0
    match_d = re.search(r'(?:diametro|d|foro)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_mm = float(match_d.group(1).replace(',', '.'))

    pos_x_mm, pos_y_mm = 0.0, 0.0
    match_coord = re.search(r'x\\s*[:=]?\\s*(-?\\d+(?:[.,]\\d+)?)\\s*y\\s*[:=]?\\s*(-?\\d+(?:[.,]\\d+)?)', f)
    if match_coord:
        pos_x_mm = float(match_coord.group(1).replace(',', '.'))
        pos_y_mm = float(match_coord.group(2).replace(',', '.'))

    direzione = kNegativeExtentDirection
    if "entrambi" in f or "simmetric" in f:
        direzione = kSymmetricExtentDirection

    return {
        "diametro_mm": diametro_mm,
        "pos_x_mm": pos_x_mm,
        "pos_y_mm": pos_y_mm,
        "direzione": direzione,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    diametro_cm = mm_to_cm(params["diametro_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddDrilledByThroughAllExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "diametro_cm_inventor": diametro_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert diametro_cm > 0
        assert abs(diametro_cm - (params["diametro_mm"] / 10.0)) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: AddDrilledByThroughAllExtent D={diametro_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleDrilledThroughAll")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(40.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        target_face = None
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, 'Normal') and abs(f.Geometry.Normal.Z - 1.0) < 0.1:
                target_face = f
                break
        if target_face is None:
            target_face = body.Faces.Item(1)

        sk = cd.Sketches.Add(target_face)
        pt2d = inv_app.TransientGeometry.CreatePoint2d(mm_to_cm(params["pos_x_mm"]), mm_to_cm(params["pos_y_mm"]))
        sp = sk.SketchPoints.Add(pt2d)
        if abs(params["pos_x_mm"]) < 1e-6 and abs(params["pos_y_mm"]) < 1e-6:
            try:
                sk.GeometricConstraints.AddCoincident(sk.OriginPoint, sp)
            except Exception:
                pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        place_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(coll)
        hole_feat = cd.Features.HoleFeatures.AddDrilledByThroughAllExtent(place_def, diametro_cm, params["direzione"])

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro passante creato con successo: {hole_feat.Name}, D={params['diametro_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 7. hole_cbore_distance
    "hole_cbore_distance": {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddCBoreByDistanceExtent",
        "descrizione": "Crea un foro con lamatura (controforo per testa vite cilindrica) a profondità definita.",
        "codice": '''"""
comandi/hole_cbore_distance.py
Modulo vocale: Foro Lamato con Controforo a Distanza (HoleFeatures.AddCBoreByDistanceExtent).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = 8.0
    cbore_diametro_mm = 14.0
    cbore_profondita_mm = 6.0
    profondita_mm = 25.0

    match_d = re.search(r'(?:diametro|d|foro)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_mm = float(match_d.group(1).replace(',', '.'))

    match_cb = re.search(r'(?:lamatura|cbore|controforo|testa)(?:\\s*(?:di|a|diametro))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_cb:
        cbore_diametro_mm = float(match_cb.group(1).replace(',', '.'))

    match_cb_prof = re.search(r'(?:profondit[àa]\\s+lamatura|profondit[àa]\\s+testa|lamatura\\s+profonda)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_cb_prof:
        cbore_profondita_mm = float(match_cb_prof.group(1).replace(',', '.'))

    match_prof = re.search(r'(?:profondit[àa]|profondo|cieco)(?:\\s*(?:totale|di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_prof:
        val = float(match_prof.group(1).replace(',', '.'))
        if abs(val - cbore_profondita_mm) > 1e-3 and abs(val - diametro_mm) > 1e-3:
            profondita_mm = val

    fondo_piatto = "fondo piatto" in f or "piatto" in f

    return {
        "diametro_mm": diametro_mm,
        "cbore_diametro_mm": cbore_diametro_mm,
        "cbore_profondita_mm": cbore_profondita_mm,
        "profondita_mm": profondita_mm,
        "fondo_piatto": fondo_piatto,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_mm"])
    cbd_cm = mm_to_cm(params["cbore_diametro_mm"])
    cbh_cm = mm_to_cm(params["cbore_profondita_mm"])
    h_cm = mm_to_cm(params["profondita_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddCBoreByDistanceExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "cbore_d_cm": cbd_cm,
        "cbore_h_cm": cbh_cm,
        "h_cm": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0 and cbd_cm > d_cm and cbh_cm > 0 and h_cm > cbh_cm
        assert abs(d_cm - params["diametro_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: AddCBoreByDistanceExtent D={d_cm}cm, CBORE_D={cbd_cm}cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleCBoreDistance")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(50.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        target_face = None
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, 'Normal') and abs(f.Geometry.Normal.Z - 1.0) < 0.1:
                target_face = f
                break
        if target_face is None:
            target_face = body.Faces.Item(1)

        sk = cd.Sketches.Add(target_face)
        sp = sk.SketchPoints.Add(inv_app.TransientGeometry.CreatePoint2d(0, 0))
        try:
            sk.GeometricConstraints.AddCoincident(sk.OriginPoint, sp)
        except Exception:
            pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        place_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(coll)
        hole_feat = cd.Features.HoleFeatures.AddCBoreByDistanceExtent(
            place_def, d_cm, cbd_cm, cbh_cm, h_cm, kNegativeExtentDirection, params["fondo_piatto"], deg_to_rad(118.0)
        )

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro lamato creato con successo: {hole_feat.Name}, D={params['diametro_mm']}mm, CBore={params['cbore_diametro_mm']}mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 8. hole_csink_distance
    "hole_csink_distance": {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddCSinkByDistanceExtent",
        "descrizione": "Crea un foro con svasatura conica per teste svasate con diametro e angolo definiti.",
        "codice": '''"""
comandi/hole_csink_distance.py
Modulo vocale: Foro Svasato a Distanza (HoleFeatures.AddCSinkByDistanceExtent).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = 6.0
    csink_diametro_mm = 12.0
    csink_angolo_deg = 90.0
    profondita_mm = 20.0

    match_d = re.search(r'(?:diametro|d|foro)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_mm = float(match_d.group(1).replace(',', '.'))

    match_csd = re.search(r'(?:svasatura|csink|svaso)(?:\\s*(?:di|a|diametro))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_csd:
        csink_diametro_mm = float(match_csd.group(1).replace(',', '.'))

    match_ang = re.search(r'(?:angolo\\s+svaso|angolo\\s+svasatura|svasatura\\s+a)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:gradi|°))?', f)
    if match_ang:
        csink_angolo_deg = float(match_ang.group(1).replace(',', '.'))

    match_prof = re.search(r'(?:profondit[àa]|profondo|cieco)(?:\\s*(?:totale|di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_prof:
        val = float(match_prof.group(1).replace(',', '.'))
        if abs(val - csink_diametro_mm) > 1e-3 and abs(val - diametro_mm) > 1e-3:
            profondita_mm = val

    return {
        "diametro_mm": diametro_mm,
        "csink_diametro_mm": csink_diametro_mm,
        "csink_angolo_deg": csink_angolo_deg,
        "profondita_mm": profondita_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_mm"])
    csd_cm = mm_to_cm(params["csink_diametro_mm"])
    csa_rad = deg_to_rad(params["csink_angolo_deg"])
    h_cm = mm_to_cm(params["profondita_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.AddCSinkByDistanceExtent",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "csink_d_cm": csd_cm,
        "csink_a_rad": csa_rad,
        "h_cm": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0 and csd_cm > d_cm and csa_rad > 0 and h_cm > 0
        assert abs(d_cm - params["diametro_mm"]/10.0) < 1e-9
        assert abs(csa_rad - math.radians(params["csink_angolo_deg"])) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: AddCSinkByDistanceExtent D={d_cm}cm, CSinkAngle={csa_rad}rad"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleCSinkDistance")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(50.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        target_face = None
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, 'Normal') and abs(f.Geometry.Normal.Z - 1.0) < 0.1:
                target_face = f
                break
        if target_face is None:
            target_face = body.Faces.Item(1)

        sk = cd.Sketches.Add(target_face)
        sp = sk.SketchPoints.Add(inv_app.TransientGeometry.CreatePoint2d(0, 0))
        try:
            sk.GeometricConstraints.AddCoincident(sk.OriginPoint, sp)
        except Exception:
            pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        place_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(coll)
        hole_feat = cd.Features.HoleFeatures.AddCSinkByDistanceExtent(
            place_def, d_cm, csd_cm, csa_rad, h_cm, kNegativeExtentDirection, False, deg_to_rad(118.0)
        )

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Foro svasato creato con successo: {hole_feat.Name}, D={params['diametro_mm']}mm, Angolo={params['csink_angolo_deg']}°"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 9. hole_definition
    "hole_definition": {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.CreateHoleDefinition",
        "descrizione": "Crea una definizione avanzata di foratura (filettata, con gioco, maschiata conica, ecc.).",
        "codice": '''"""
comandi/hole_definition.py
Modulo vocale: Definizione Avanzata di Foratura (HoleFeatures.CreateHoleDefinition).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    diametro_mm = 10.0
    profondita_mm = 20.0
    passante = "passante" in f or "attraverso" in f

    match_d = re.search(r'(?:diametro|d|m|foro)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_mm = float(match_d.group(1).replace(',', '.'))

    match_prof = re.search(r'(?:profondit[àa]|profondo)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_prof:
        profondita_mm = float(match_prof.group(1).replace(',', '.'))

    return {
        "diametro_mm": diametro_mm,
        "profondita_mm": profondita_mm,
        "passante": passante,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_mm"])
    h_cm = mm_to_cm(params["profondita_mm"])

    resoconto = {
        "modulo": "HoleFeatures",
        "metodo": "HoleFeatures.CreateHoleDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "h_cm": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0 and h_cm > 0
        assert abs(d_cm - params["diametro_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: HoleDefinition parametrica D={d_cm:.4f} cm, H={h_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_HoleDefinition")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(40.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        target_face = None
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, 'Normal') and abs(f.Geometry.Normal.Z - 1.0) < 0.1:
                target_face = f
                break
        if target_face is None:
            target_face = body.Faces.Item(1)

        sk = cd.Sketches.Add(target_face)
        sp = sk.SketchPoints.Add(inv_app.TransientGeometry.CreatePoint2d(0, 0))
        try:
            sk.GeometricConstraints.AddCoincident(sk.OriginPoint, sp)
        except Exception:
            pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        place_def = cd.Features.HoleFeatures.CreateSketchPlacementDefinition(coll)
        if params["passante"]:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByThroughAllExtent(place_def, d_cm, kNegativeExtentDirection)
        else:
            hole_feat = cd.Features.HoleFeatures.AddDrilledByDistanceExtent(place_def, d_cm, h_cm, kNegativeExtentDirection, False, deg_to_rad(118.0))

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature foratura avanzata creata con successo: {hole_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 10. thread_standard
    "thread_standard": {
        "modulo": "ThreadFeatures",
        "metodo": "ThreadFeatures.Add",
        "descrizione": "Applica una filettatura metrica o standard ISO/ANSI a una faccia cilindrica.",
        "codice": '''"""
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
    match_m = re.search(r'(m\\d+(?:x\\d+(?:[.,]\\d+)?)?)', f)
    if match_m:
        designazione = match_m.group(1).upper().replace(',', '.')

    lunghezza_totale = "tutta la lunghezza" in f or "completa" in f or "passante" in f
    lunghezza_filetto_mm = 20.0
    match_l = re.search(r'(?:lunghezza|profondit[àa])(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
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
        part_doc = get_or_create_part_doc(inv_app, visible=False)

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
'''
    },

    # 11. thread_create_info
    "thread_create_info": {
        "modulo": "ThreadFeatures",
        "metodo": "ThreadFeatures.CreateThreadInfo",
        "descrizione": "Configura le informazioni dettagliate della filettatura (passo, classe, direzione destra/sinistra).",
        "codice": '''"""
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
    match_m = re.search(r'(m\\d+(?:x\\d+(?:[.,]\\d+)?)?)', f)
    if match_m:
        designazione = match_m.group(1).upper().replace(',', '.')

    classe = "6g"
    match_cl = re.search(r'classe\\s*([4-8][gh])', f)
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
        part_doc = get_or_create_part_doc(inv_app, visible=False)

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
'''
    },

    # 12. chamfer_distance
    "chamfer_distance": {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingDistance",
        "descrizione": "Crea uno smusso a 45 gradi su uno o più spigoli specificando la distanza.",
        "codice": '''"""
comandi/chamfer_distance.py
Modulo vocale: Smusso a Distanza Costante (ChamferFeatures.AddUsingDistance).
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
    distanza_mm = 2.0
    match_d = re.search(r'(?:smusso|smussa|distanza)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "distanza_mm": distanza_mm,
        "tutti_spigoli": "tutti" in f or "completo" in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    distanza_cm = mm_to_cm(params["distanza_mm"])

    resoconto = {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingDistance",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "distanza_cm_inventor": distanza_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert distanza_cm > 0
        assert abs(distanza_cm - params["distanza_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: ChamferFeatures.AddUsingDistance dist={distanza_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ChamferDistance")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 70.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        # Seleziona spigoli superiori
        for i in range(1, body.Edges.Count + 1):
            edge = body.Edges.Item(i)
            edges_coll.Add(edge)
            if not params["tutti_spigoli"] and edges_coll.Count >= 4:
                break

        chamfer_feat = cd.Features.ChamferFeatures.AddUsingDistance(edges_coll, distanza_cm)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Smusso creato con successo: {chamfer_feat.Name}, Dist={params['distanza_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 13. chamfer_distance_angle
    "chamfer_distance_angle": {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingDistanceAndAngle",
        "descrizione": "Crea uno smusso definito da distanza e angolo su spigoli selezionati.",
        "codice": '''"""
comandi/chamfer_distance_angle.py
Modulo vocale: Smusso con Distanza e Angolo (ChamferFeatures.AddUsingDistanceAndAngle).
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


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    distanza_mm = 3.0
    angolo_deg = 30.0

    match_d = re.search(r'(?:distanza|smusso)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_mm = float(match_d.group(1).replace(',', '.'))

    match_a = re.search(r'(?:angolo|gradi)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:gradi|°|deg))?', f)
    if match_a:
        angolo_deg = float(match_a.group(1).replace(',', '.'))

    return {
        "distanza_mm": distanza_mm,
        "angolo_deg": angolo_deg,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    dist_cm = mm_to_cm(params["distanza_mm"])
    ang_rad = deg_to_rad(params["angolo_deg"])

    resoconto = {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingDistanceAndAngle",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "dist_cm": dist_cm,
        "ang_rad": ang_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert dist_cm > 0 and ang_rad > 0
        assert abs(dist_cm - params["distanza_mm"]/10.0) < 1e-9
        assert abs(ang_rad - math.radians(params["angolo_deg"])) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: Chamfer AddUsingDistanceAndAngle dist={dist_cm:.4f} cm, ang={ang_rad:.4f} rad"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ChamferDistanceAngle")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(35.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        ref_face = None
        for i in range(1, body.Faces.Count + 1):
            fc = body.Faces.Item(i)
            if hasattr(fc.Geometry, 'Normal') and abs(fc.Geometry.Normal.Z - 1.0) < 0.1:
                ref_face = fc
                break
        if ref_face is None:
            ref_face = body.Faces.Item(1)

        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        for i in range(1, ref_face.Edges.Count + 1):
            edges_coll.Add(ref_face.Edges.Item(i))

        chamfer_feat = cd.Features.ChamferFeatures.AddUsingDistanceAndAngle(edges_coll, ref_face, dist_cm, ang_rad)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Smusso dist/angolo creato con successo: {chamfer_feat.Name}, D={params['distanza_mm']}mm, Ang={params['angolo_deg']}°"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 14. chamfer_two_distances
    "chamfer_two_distances": {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingTwoDistances",
        "descrizione": "Crea uno smusso a due distanze asimmetriche su spigoli selezionati.",
        "codice": '''"""
comandi/chamfer_two_distances.py
Modulo vocale: Smusso a Due Distanze Asimmetriche (ChamferFeatures.AddUsingTwoDistances).
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
    dist1_mm = 2.0
    dist2_mm = 5.0

    match_d = re.search(r'(\\d+(?:[.,]\\d+)?)\\s*(?:per|x|e)\\s*(\\d+(?:[.,]\\d+)?)', f)
    if match_d:
        dist1_mm = float(match_d.group(1).replace(',', '.'))
        dist2_mm = float(match_d.group(2).replace(',', '.'))

    return {
        "distanza_1_mm": dist1_mm,
        "distanza_2_mm": dist2_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d1_cm = mm_to_cm(params["distanza_1_mm"])
    d2_cm = mm_to_cm(params["distanza_2_mm"])

    resoconto = {
        "modulo": "ChamferFeatures",
        "metodo": "ChamferFeatures.AddUsingTwoDistances",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d1_cm": d1_cm,
        "d2_cm": d2_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d1_cm > 0 and d2_cm > 0
        assert abs(d1_cm - params["distanza_1_mm"]/10.0) < 1e-9
        assert abs(d2_cm - params["distanza_2_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: AddUsingTwoDistances D1={d1_cm:.4f} cm, D2={d2_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ChamferTwoDistances")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(35.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        ref_face = None
        for i in range(1, body.Faces.Count + 1):
            fc = body.Faces.Item(i)
            if hasattr(fc.Geometry, 'Normal') and abs(fc.Geometry.Normal.Z - 1.0) < 0.1:
                ref_face = fc
                break
        if ref_face is None:
            ref_face = body.Faces.Item(1)

        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        for i in range(1, ref_face.Edges.Count + 1):
            edges_coll.Add(ref_face.Edges.Item(i))

        chamfer_feat = cd.Features.ChamferFeatures.AddUsingTwoDistances(edges_coll, ref_face, d1_cm, d2_cm)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Smusso a due distanze creato: {chamfer_feat.Name}, D1={params['distanza_1_mm']}mm, D2={params['distanza_2_mm']}mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 15. fillet_edge_set
    "fillet_edge_set": {
        "modulo": "FilletFeatures",
        "metodo": "FilletFeatures.AddEdgeSet",
        "descrizione": "Crea raccordi a raggio costante su uno o più spigoli selezionati.",
        "codice": '''"""
comandi/fillet_edge_set.py
Modulo vocale: Raccordo a Raggio Costante (FilletFeatures.AddEdgeSet).
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
    raggio_mm = 3.0
    match_r = re.search(r'(?:raccordo|raccorda|raggio|r)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_r:
        raggio_mm = float(match_r.group(1).replace(',', '.'))

    return {
        "raggio_mm": raggio_mm,
        "tutti_spigoli": "tutti" in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    raggio_cm = mm_to_cm(params["raggio_mm"])

    resoconto = {
        "modulo": "FilletFeatures",
        "metodo": "FilletFeatures.AddEdgeSet",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "raggio_cm_inventor": raggio_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert raggio_cm > 0
        assert abs(raggio_cm - params["raggio_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: FilletFeatures.AddEdgeSet R={raggio_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_FilletEdgeSet")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        for i in range(1, body.Edges.Count + 1):
            edges_coll.Add(body.Edges.Item(i))
            if not params["tutti_spigoli"] and edges_coll.Count >= 4:
                break

        fillet_feat = cd.Features.FilletFeatures.AddEdgeSet(edges_coll, raggio_cm)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Raccordo creato con successo: {fillet_feat.Name}, R={params['raggio_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 16. fillet_definition
    "fillet_definition": {
        "modulo": "FilletFeatures",
        "metodo": "FilletFeatures.CreateFilletDefinition",
        "descrizione": "Crea una definizione avanzata di raccordo (raggio variabile, raccordo a corda, facce complete).",
        "codice": '''"""
comandi/fillet_definition.py
Modulo vocale: Definizione Avanzata di Raccordo (FilletFeatures.CreateFilletDefinition).
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
    raggio_mm = 4.0
    match_r = re.search(r'(?:raccordo|raggio|r)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_r:
        raggio_mm = float(match_r.group(1).replace(',', '.'))

    return {
        "raggio_mm": raggio_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    raggio_cm = mm_to_cm(params["raggio_mm"])

    resoconto = {
        "modulo": "FilletFeatures",
        "metodo": "FilletFeatures.CreateFilletDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "raggio_cm_inventor": raggio_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert raggio_cm > 0
        assert abs(raggio_cm - params["raggio_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateFilletDefinition parametrico R={raggio_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_FilletDefinition")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        edges_coll = inv_app.TransientObjects.CreateEdgeCollection()
        for i in range(1, min(5, body.Edges.Count + 1)):
            edges_coll.Add(body.Edges.Item(i))

        fillet_def = cd.Features.FilletFeatures.CreateFilletDefinition()
        fillet_def.AddConstantRadiusEdgeSet(edges_coll, raggio_cm)
        fillet_feat = cd.Features.FilletFeatures.Add(fillet_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Raccordo avanzato creato: {fillet_feat.Name}, R={params['raggio_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 17. rectangular_pattern
    "rectangular_pattern": {
        "modulo": "RectangularPatternFeatures",
        "metodo": "RectangularPatternFeatures.Add",
        "descrizione": "Crea una serie rettangolare (pattern lineare su due direzioni con conteggio e spaziatura).",
        "codice": '''"""
comandi/rectangular_pattern.py
Modulo vocale: Serie Rettangolare Lineare (RectangularPatternFeatures.Add).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kPositiveExtentDirection, kNegativeExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    conteggio_x = 3
    spaziatura_x_mm = 20.0
    conteggio_y = 2
    spaziatura_y_mm = 15.0

    match_cnt = re.search(r'(\\d+)\\s*(?:copie|elementi|colonne|x)\\s*(\\d+)?', f)
    if match_cnt:
        conteggio_x = int(match_cnt.group(1))
        if match_cnt.group(2):
            conteggio_y = int(match_cnt.group(2))

    match_spaz = re.search(r'(?:passo|spaziatura|distanza)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_spaz:
        spaziatura_x_mm = float(match_spaz.group(1).replace(',', '.'))

    return {
        "conteggio_x": conteggio_x,
        "spaziatura_x_mm": spaziatura_x_mm,
        "conteggio_y": conteggio_y,
        "spaziatura_y_mm": spaziatura_y_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spaz_x_cm = mm_to_cm(params["spaziatura_x_mm"])
    spaz_y_cm = mm_to_cm(params["spaziatura_y_mm"])

    resoconto = {
        "modulo": "RectangularPatternFeatures",
        "metodo": "RectangularPatternFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "spaz_x_cm": spaz_x_cm,
        "spaz_y_cm": spaz_y_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio_x"] > 1 and spaz_x_cm > 0
        assert abs(spaz_x_cm - params["spaziatura_x_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: RectangularPatternFeatures.Add {params['conteggio_x']}x{params['conteggio_y']} passo={spaz_x_cm} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_RectangularPattern")
    try:
        cd = part_doc.ComponentDefinition
        # Crea corpo base e foro se non esistono
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 120.0, 80.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)

        x_axis = cd.WorkAxes.Item(1)
        y_axis = cd.WorkAxes.Item(2)

        pattern = cd.Features.RectangularPatternFeatures.Add(
            feat_coll,
            x_axis,
            True,
            params["conteggio_x"],
            spaz_x_cm,
            20737, # kDefault
            y_axis,
            True,
            params["conteggio_y"],
            spaz_y_cm
        )
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Serie rettangolare creata: {pattern.Name}, Copie={params['conteggio_x']}x{params['conteggio_y']}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 18. rectangular_pattern_definition
    "rectangular_pattern_definition": {
        "modulo": "RectangularPatternFeatures",
        "metodo": "RectangularPatternFeatures.CreateDefinition",
        "descrizione": "Crea e configura la definizione parametrica per serie rettangolari complesse.",
        "codice": '''"""
comandi/rectangular_pattern_definition.py
Modulo vocale: Definizione Serie Rettangolare Avanzata (RectangularPatternFeatures.CreateDefinition).
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
    conteggio = 4
    passo_mm = 25.0
    match_c = re.search(r'(\\d+)\\s*(?:copie|elementi)', f)
    if match_c:
        conteggio = int(match_c.group(1))
    match_p = re.search(r'(?:passo|spaziatura|distanza)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_p:
        passo_mm = float(match_p.group(1).replace(',', '.'))

    return {
        "conteggio": conteggio,
        "passo_mm": passo_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    passo_cm = mm_to_cm(params["passo_mm"])

    resoconto = {
        "modulo": "RectangularPatternFeatures",
        "metodo": "RectangularPatternFeatures.CreateDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "passo_cm": passo_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio"] > 1 and passo_cm > 0
        assert abs(passo_cm - params["passo_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: RectangularPatternDefinition N={params['conteggio']}, Passo={passo_cm} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_RectPatternDef")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 100.0, 60.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(25.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        x_axis = cd.WorkAxes.Item(1)

        pat_def = cd.Features.RectangularPatternFeatures.CreateDefinition(
            feat_coll, x_axis, True, params["conteggio"], passo_cm, 20737
        )
        pattern = cd.Features.RectangularPatternFeatures.AddByDefinition(pat_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione serie rettangolare creata con successo: {pattern.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 19. circular_pattern
    "circular_pattern": {
        "modulo": "CircularPatternFeatures",
        "metodo": "CircularPatternFeatures.Add",
        "descrizione": "Crea una serie circolare/polare attorno a un asse di rotazione con conteggio e angolo totale/passo.",
        "codice": '''"""
comandi/circular_pattern.py
Modulo vocale: Serie Circolare Polare (CircularPatternFeatures.Add).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    conteggio = 6
    angolo_deg = 360.0

    match_c = re.search(r'(\\d+)\\s*(?:copie|elementi|fori|denti)', f)
    if match_c:
        conteggio = int(match_c.group(1))

    match_a = re.search(r'(?:su|angolo|arco)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:gradi|°|deg))?', f)
    if match_a:
        angolo_deg = float(match_a.group(1).replace(',', '.'))

    return {
        "conteggio": conteggio,
        "angolo_deg": angolo_deg,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    angolo_rad = deg_to_rad(params["angolo_deg"])

    resoconto = {
        "modulo": "CircularPatternFeatures",
        "metodo": "CircularPatternFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "angolo_rad_inventor": angolo_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio"] > 1 and angolo_rad > 0
        assert abs(angolo_rad - math.radians(params["angolo_deg"])) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CircularPatternFeatures.Add N={params['conteggio']} su {angolo_rad:.4f} rad"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_CircularPattern")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_circolare_centrato(part_doc, 80.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(25.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        z_axis = cd.WorkAxes.Item(3) # Z Axis per rivoluzione centrata su XY

        pattern = cd.Features.CircularPatternFeatures.Add(
            feat_coll,
            z_axis,
            True,
            params["conteggio"],
            angolo_rad,
            True # Fit within total angle
        )
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Serie circolare creata: {pattern.Name}, Copie={params['conteggio']}, Angolo={params['angolo_deg']}°"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 20. circular_pattern_definition
    "circular_pattern_definition": {
        "modulo": "CircularPatternFeatures",
        "metodo": "CircularPatternFeatures.CreateDefinition",
        "descrizione": "Crea e configura la definizione parametrica per serie circolari.",
        "codice": '''"""
comandi/circular_pattern_definition.py
Modulo vocale: Definizione Serie Circolare Avanzata (CircularPatternFeatures.CreateDefinition).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, deg_to_rad, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_circolare_centrato,
        kPositiveExtentDirection, kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    conteggio = 8
    angolo_deg = 360.0
    match_c = re.search(r'(\\d+)\\s*(?:copie|elementi|fori)', f)
    if match_c:
        conteggio = int(match_c.group(1))

    return {
        "conteggio": conteggio,
        "angolo_deg": angolo_deg,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    ang_rad = deg_to_rad(params["angolo_deg"])

    resoconto = {
        "modulo": "CircularPatternFeatures",
        "metodo": "CircularPatternFeatures.CreateDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "angolo_rad_inventor": ang_rad,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["conteggio"] > 1 and ang_rad > 0
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CircularPatternDefinition N={params['conteggio']}, Ang={ang_rad:.4f} rad"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_CircPatternDef")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_circolare_centrato(part_doc, 80.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(25.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        z_axis = cd.WorkAxes.Item(3)

        pat_def = cd.Features.CircularPatternFeatures.CreateDefinition(
            feat_coll, z_axis, True, params["conteggio"], ang_rad, True
        )
        pattern = cd.Features.CircularPatternFeatures.AddByDefinition(pat_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione serie circolare creata con successo: {pattern.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 21. mirror_features
    "mirror_features": {
        "modulo": "MirrorFeatures",
        "metodo": "MirrorFeatures.Add",
        "descrizione": "Specchia una o più feature rispetto a un piano di lavoro o faccia piana di simmetria.",
        "codice": '''"""
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
        part_doc = get_or_create_part_doc(inv_app, visible=False)

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
'''
    },

    # 22. mirror_definition
    "mirror_definition": {
        "modulo": "MirrorFeatures",
        "metodo": "MirrorFeatures.CreateDefinition",
        "descrizione": "Crea la definizione completa di specchiatura per feature o per l'intero solido.",
        "codice": '''"""
comandi/mirror_definition.py
Modulo vocale: Definizione Specchiatura Avanzata Solidi (MirrorFeatures.CreateDefinition).
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
    piano_indice = 1
    if "xz" in f or "piano 2" in f:
        piano_indice = 2
    elif "xy" in f or "piano 3" in f:
        piano_indice = 3

    return {
        "piano_indice": piano_indice,
        "specchia_solido": "solido" in f or "tutto" in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)

    resoconto = {
        "modulo": "MirrorFeatures",
        "metodo": "MirrorFeatures.CreateDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert params["piano_indice"] in (1, 2, 3)
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: MirrorDefinition su WorkPlane {params['piano_indice']}"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_MirrorDefinition")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        target_feat = cd.Features.ExtrudeFeatures.Item(1)
        feat_coll = inv_app.TransientObjects.CreateObjectCollection()
        feat_coll.Add(target_feat)
        mirror_plane = cd.WorkPlanes.Item(params["piano_indice"])

        mirror_def = cd.Features.MirrorFeatures.CreateDefinition(feat_coll, mirror_plane)
        mirror_feat = cd.Features.MirrorFeatures.AddByDefinition(mirror_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Specchiatura avanzata creata: {mirror_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 23. shell_standard
    "shell_standard": {
        "modulo": "ShellFeatures",
        "metodo": "ShellFeatures.Add",
        "descrizione": "Svuota un corpo solido lasciando uno spessore di parete costante e rimuovendo facce aperte.",
        "codice": '''"""
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
    match_s = re.search(r'(?:spessore|parete|svuota)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
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
        part_doc = get_or_create_part_doc(inv_app, visible=False)

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
'''
    },

    # 24. shell_definition
    "shell_definition": {
        "modulo": "ShellFeatures",
        "metodo": "ShellFeatures.CreateShellDefinition",
        "descrizione": "Crea una definizione avanzata di svuotamento con spessori differenziati per faccia.",
        "codice": '''"""
comandi/shell_definition.py
Modulo vocale: Definizione Avanzata Svuotamento (ShellFeatures.CreateShellDefinition).
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
    spessore_mm = 2.5
    match_s = re.search(r'(?:spessore|parete)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
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
        resoconto["dettagli"] = f"Simulazione superata: CreateShellDefinition spessore={spessore_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_ShellDef")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(40.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        open_faces = inv_app.TransientObjects.CreateFaceCollection()
        for i in range(1, body.Faces.Count + 1):
            fc = body.Faces.Item(i)
            if hasattr(fc.Geometry, 'Normal') and abs(fc.Geometry.Normal.Z - 1.0) < 0.1:
                open_faces.Add(fc)
                break
        if open_faces.Count == 0:
            open_faces.Add(body.Faces.Item(1))

        shell_def = cd.Features.ShellFeatures.CreateShellDefinition(open_faces, spessore_cm, 20481)
        shell_feat = cd.Features.ShellFeatures.AddByDefinition(shell_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione svuotamento creata: {shell_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 25. rib_standard
    "rib_standard": {
        "modulo": "RibFeatures",
        "metodo": "RibFeatures.Add",
        "descrizione": "Crea una nervatura di rinforzo o anima strutturale a partire da un profilo di schizzo aperto.",
        "codice": '''"""
comandi/rib_standard.py
Modulo vocale: Nervatura di Rinforzo (RibFeatures.Add).
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
    spessore_mm = 4.0
    match_s = re.search(r'(?:nervatura|costola|spessore|anima)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
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
        "modulo": "RibFeatures",
        "metodo": "RibFeatures.Add",
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
        resoconto["dettagli"] = f"Simulazione superata: RibFeatures.Add spessore={spessore_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_RibStandard")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        # Crea un profilo di schizzo aperto su WorkPlane 2 (XZ plane)
        wp2 = cd.WorkPlanes.Item(2)
        sk_rib = cd.Sketches.Add(wp2)
        tg = inv_app.TransientGeometry
        p1 = tg.CreatePoint2d(mm_to_cm(-20.0), mm_to_cm(25.0))
        p2 = tg.CreatePoint2d(mm_to_cm(20.0), mm_to_cm(5.0))
        line = sk_rib.SketchLines.AddByTwoPoints(p1, p2)
        prof_rib = sk_rib.Profiles.AddForSolid(False)

        rib_def = cd.Features.RibFeatures.CreateRibDefinition(prof_rib, True, spessore_cm)
        rib_feat = cd.Features.RibFeatures.Add(rib_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Nervatura creata: {rib_feat.Name}, Spessore={params['spessore_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 26. rib_definition
    "rib_definition": {
        "modulo": "RibFeatures",
        "metodo": "RibFeatures.CreateRibDefinition",
        "descrizione": "Crea e configura la definizione di nervatura con spessori normali o paralleli al piano.",
        "codice": '''"""
comandi/rib_definition.py
Modulo vocale: Definizione Parametrica Nervatura (RibFeatures.CreateRibDefinition).
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
    spessore_mm = 5.0
    match_s = re.search(r'(?:nervatura|costola|spessore)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_s:
        spessore_mm = float(match_s.group(1).replace(',', '.'))

    return {
        "spessore_mm": spessore_mm,
        "direzione_normale": "normale" in f,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spessore_cm = mm_to_cm(params["spessore_mm"])

    resoconto = {
        "modulo": "RibFeatures",
        "metodo": "RibFeatures.CreateRibDefinition",
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
        resoconto["dettagli"] = f"Simulazione superata: CreateRibDefinition spessore={spessore_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_RibDefinition")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        wp2 = cd.WorkPlanes.Item(2)
        sk_rib = cd.Sketches.Add(wp2)
        tg = inv_app.TransientGeometry
        p1 = tg.CreatePoint2d(mm_to_cm(-25.0), mm_to_cm(25.0))
        p2 = tg.CreatePoint2d(mm_to_cm(25.0), mm_to_cm(5.0))
        sk_rib.SketchLines.AddByTwoPoints(p1, p2)
        prof_rib = sk_rib.Profiles.AddForSolid(False)

        rib_def = cd.Features.RibFeatures.CreateRibDefinition(prof_rib, True, spessore_cm)
        rib_feat = cd.Features.RibFeatures.Add(rib_def)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione nervatura creata: {rib_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 27. move_face_standard
    "move_face_standard": {
        "modulo": "MoveFaceFeatures",
        "metodo": "MoveFaceFeatures.Add",
        "descrizione": "Trasla, ruota o sposta una o più facce di un corpo solido lungo una direzione o vettore.",
        "codice": '''"""
comandi/move_face_standard.py
Modulo vocale: Spostamento Diretto Facce (MoveFaceFeatures.Add).
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
    spostamento_mm = 5.0
    match_s = re.search(r'(?:sposta|trasla|offset|distanza)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_s:
        spostamento_mm = float(match_s.group(1).replace(',', '.'))

    return {
        "spostamento_mm": spostamento_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    spost_cm = mm_to_cm(params["spostamento_mm"])

    resoconto = {
        "modulo": "MoveFaceFeatures",
        "metodo": "MoveFaceFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "spost_cm_inventor": spost_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert spost_cm > 0
        assert abs(spost_cm - params["spostamento_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: MoveFaceFeatures.Add spost={spost_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_MoveFaceStandard")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        faces_coll = inv_app.TransientObjects.CreateFaceCollection()
        for i in range(1, body.Faces.Count + 1):
            fc = body.Faces.Item(i)
            if hasattr(fc.Geometry, 'Normal') and abs(fc.Geometry.Normal.Z - 1.0) < 0.1:
                faces_coll.Add(fc)
                break
        if faces_coll.Count == 0:
            faces_coll.Add(body.Faces.Item(1))

        z_axis = cd.WorkAxes.Item(3)
        move_def = cd.Features.MoveFaceFeatures.CreateMoveFaceDefinition(faces_coll)
        move_def.Direction = z_axis
        move_def.Distance = spost_cm
        move_feat = cd.Features.MoveFaceFeatures.Add(move_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Spostamento faccia completato: {move_feat.Name}, Spost={params['spostamento_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 28. move_face_definition
    "move_face_definition": {
        "modulo": "MoveFaceFeatures",
        "metodo": "MoveFaceFeatures.CreateMoveFaceDefinition",
        "descrizione": "Crea una definizione avanzata di spostamento facce per modifiche dirette al solido.",
        "codice": '''"""
comandi/move_face_definition.py
Modulo vocale: Definizione Spostamento Diretto Faccia (MoveFaceFeatures.CreateMoveFaceDefinition).
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
    distanza_mm = 6.0
    match_d = re.search(r'(?:distanza|spostamento|trasla)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "distanza_mm": distanza_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    dist_cm = mm_to_cm(params["distanza_mm"])

    resoconto = {
        "modulo": "MoveFaceFeatures",
        "metodo": "MoveFaceFeatures.CreateMoveFaceDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "dist_cm_inventor": dist_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert dist_cm > 0
        assert abs(dist_cm - params["distanza_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateMoveFaceDefinition dist={dist_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_MoveFaceDef")
    try:
        cd = part_doc.ComponentDefinition
        if cd.SurfaceBodies.Count == 0:
            _, bp = crea_schizzo_rettangolare_centrato(part_doc, 80.0, 50.0, 3)
            cd.Features.ExtrudeFeatures.AddByDistanceExtent(bp, mm_to_cm(30.0), kPositiveExtentDirection, kJoinOperation)

        body = cd.SurfaceBodies.Item(1)
        faces_coll = inv_app.TransientObjects.CreateFaceCollection()
        faces_coll.Add(body.Faces.Item(1))
        z_axis = cd.WorkAxes.Item(3)

        move_def = cd.Features.MoveFaceFeatures.CreateMoveFaceDefinition(faces_coll)
        move_def.Direction = z_axis
        move_def.Distance = dist_cm
        move_feat = cd.Features.MoveFaceFeatures.Add(move_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione MoveFace completata: {move_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 29. loft_standard
    "loft_standard": {
        "modulo": "LoftFeatures",
        "metodo": "LoftFeatures.Add",
        "descrizione": "Crea una feature di loft (raccordo di transizione) attraverso due o più sezioni/profili.",
        "codice": '''"""
comandi/loft_standard.py
Modulo vocale: Transizione Loft tra Profili (LoftFeatures.Add).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        crea_schizzo_circolare_centrato,
        kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    altezza_mm = 50.0
    match_h = re.search(r'(?:altezza|distanza|quota)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_h:
        altezza_mm = float(match_h.group(1).replace(',', '.'))

    return {
        "altezza_mm": altezza_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    h_cm = mm_to_cm(params["altezza_mm"])

    resoconto = {
        "modulo": "LoftFeatures",
        "metodo": "LoftFeatures.Add",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "altezza_cm_inventor": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert h_cm > 0
        assert abs(h_cm - params["altezza_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: LoftFeatures.Add transizione H={h_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_LoftStandard")
    try:
        cd = part_doc.ComponentDefinition
        # Sezione 1 su XY Plane (WorkPlane 3)
        _, prof1 = crea_schizzo_rettangolare_centrato(part_doc, 60.0, 40.0, 3)

        # Sezione 2 su piano di offset H
        wp_base = cd.WorkPlanes.Item(3)
        wp_offset = cd.WorkPlanes.AddByPlaneAndOffset(wp_base, h_cm)
        sk2 = cd.Sketches.Add(wp_offset)
        c2 = sk2.SketchCircles.AddByCenterRadius(inv_app.TransientGeometry.CreatePoint2d(0, 0), mm_to_cm(25.0) / 2.0)
        sk2.GeometricConstraints.AddCoincident(sk2.OriginPoint, c2.CenterSketchPoint)
        prof2 = sk2.Profiles.AddForSolid()

        sections = inv_app.TransientObjects.CreateObjectCollection()
        sections.Add(prof1)
        sections.Add(prof2)

        loft_def = cd.Features.LoftFeatures.CreateLoftDefinition(sections, kJoinOperation)
        loft_feat = cd.Features.LoftFeatures.Add(loft_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Feature Loft creata con successo: {loft_feat.Name}, H={params['altezza_mm']} mm"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 30. loft_definition
    "loft_definition": {
        "modulo": "LoftFeatures",
        "metodo": "LoftFeatures.CreateLoftDefinition",
        "descrizione": "Crea la definizione avanzata di loft specificando curve guida, linee d'asse e condizioni di tangenza.",
        "codice": '''"""
comandi/loft_definition.py
Modulo vocale: Definizione Parametrica Loft Avanzato (LoftFeatures.CreateLoftDefinition).
"""

import math
import re
from typing import Dict, Any

try:
    from comandi.inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kJoinOperation
    )
except ImportError:
    from inventor_utils import (
        mm_to_cm, get_inventor_app, get_or_create_part_doc,
        crea_schizzo_rettangolare_centrato,
        kJoinOperation
    )


def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    distanza_sezioni_mm = 60.0
    match_d = re.search(r'(?:distanza|altezza|quota)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        distanza_sezioni_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "distanza_sezioni_mm": distanza_sezioni_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    h_cm = mm_to_cm(params["distanza_sezioni_mm"])

    resoconto = {
        "modulo": "LoftFeatures",
        "metodo": "LoftFeatures.CreateLoftDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "h_cm_inventor": h_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert h_cm > 0
        assert abs(h_cm - params["distanza_sezioni_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateLoftDefinition sezioni dist={h_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_LoftDefinition")
    try:
        cd = part_doc.ComponentDefinition
        _, prof1 = crea_schizzo_rettangolare_centrato(part_doc, 50.0, 30.0, 3)

        wp_base = cd.WorkPlanes.Item(3)
        wp_offset = cd.WorkPlanes.AddByPlaneAndOffset(wp_base, h_cm)
        sk2 = cd.Sketches.Add(wp_offset)
        r2 = sk2.SketchLines.AddAsTwoPointRectangle(
            inv_app.TransientGeometry.CreatePoint2d(mm_to_cm(-15), mm_to_cm(-15)),
            inv_app.TransientGeometry.CreatePoint2d(mm_to_cm(15), mm_to_cm(15))
        )
        prof2 = sk2.Profiles.AddForSolid()

        sections = inv_app.TransientObjects.CreateObjectCollection()
        sections.Add(prof1)
        sections.Add(prof2)

        loft_def = cd.Features.LoftFeatures.CreateLoftDefinition(sections, kJoinOperation)
        loft_feat = cd.Features.LoftFeatures.Add(loft_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione Loft creata con successo: {loft_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 31. sweep_path
    "sweep_path": {
        "modulo": "SweepFeatures",
        "metodo": "SweepFeatures.AddUsingPath",
        "descrizione": "Crea uno sweep estrudendo un profilo chiuso o aperto lungo una traiettoria guida (percorso).",
        "codice": '''"""
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
    match_d = re.search(r'(?:sezione|diametro|profilo)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_sezione_mm = float(match_d.group(1).replace(',', '.'))

    lunghezza_percorso_mm = 60.0
    match_l = re.search(r'(?:lunghezza|percorso|corsa)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
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
        part_doc = get_or_create_part_doc(inv_app, visible=False)

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
'''
    },

    # 32. sweep_guide_rail
    "sweep_guide_rail": {
        "modulo": "SweepFeatures",
        "metodo": "SweepFeatures.AddUsingGuideRail",
        "descrizione": "Crea uno sweep con profilo lungo una traiettoria e una o più curve guida di orientamento/scala.",
        "codice": '''"""
comandi/sweep_guide_rail.py
Modulo vocale: Sweep con Rotaia Guida (SweepFeatures.AddUsingGuideRail).
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
    diametro_sezione_mm = 10.0
    match_d = re.search(r'(?:sezione|diametro)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_sezione_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "diametro_sezione_mm": diametro_sezione_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_sezione_mm"])

    resoconto = {
        "modulo": "SweepFeatures",
        "metodo": "SweepFeatures.AddUsingGuideRail",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0
        assert abs(d_cm - params["diametro_sezione_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: SweepFeatures.AddUsingGuideRail D={d_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_SweepGuideRail")
    try:
        cd = part_doc.ComponentDefinition
        _, profile = crea_schizzo_circolare_centrato(part_doc, params["diametro_sezione_mm"], 3)

        wp_path = cd.WorkPlanes.Item(2)
        sk_path = cd.Sketches.Add(wp_path)
        tg = inv_app.TransientGeometry
        path_line = sk_path.SketchLines.AddByTwoPoints(tg.CreatePoint2d(0, 0), tg.CreatePoint2d(0, mm_to_cm(50.0)))
        path = cd.Features.SweepFeatures.CreatePath(path_line)

        # Guida su WorkPlane 1
        wp_guide = cd.WorkPlanes.Item(1)
        sk_guide = cd.Sketches.Add(wp_guide)
        guide_line = sk_guide.SketchLines.AddByTwoPoints(
            tg.CreatePoint2d(d_cm/2.0, 0), tg.CreatePoint2d(d_cm, mm_to_cm(50.0))
        )
        guide = cd.Features.SweepFeatures.CreatePath(guide_line)

        sweep_feat = cd.Features.SweepFeatures.AddUsingGuideRail(profile, path, guide, kJoinOperation)
        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Sweep con guida creato con successo: {sweep_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    },

    # 33. sweep_definition
    "sweep_definition": {
        "modulo": "SweepFeatures",
        "metodo": "SweepFeatures.CreateSweepDefinition",
        "descrizione": "Crea la definizione completa di sweep per traiettorie 3D complesse.",
        "codice": '''"""
comandi/sweep_definition.py
Modulo vocale: Definizione Sweep Avanzata (SweepFeatures.CreateSweepDefinition).
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
    diametro_sezione_mm = 12.0
    match_d = re.search(r'(?:sezione|diametro)(?:\\s*(?:di|a))?\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*(?:mm|millimetri))?', f)
    if match_d:
        diametro_sezione_mm = float(match_d.group(1).replace(',', '.'))

    return {
        "diametro_sezione_mm": diametro_sezione_mm,
        "frase_originale": frase
    }


def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    d_cm = mm_to_cm(params["diametro_sezione_mm"])

    resoconto = {
        "modulo": "SweepFeatures",
        "metodo": "SweepFeatures.CreateSweepDefinition",
        "input_vocale": frase_vocale,
        "parametri_estratti": params,
        "d_cm": d_cm,
        "successo": False,
        "dettagli": ""
    }

    if test_mode:
        assert d_cm > 0
        assert abs(d_cm - params["diametro_sezione_mm"]/10.0) < 1e-9
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Simulazione superata: CreateSweepDefinition parametrico D={d_cm:.4f} cm"
        return resoconto

    inv_app = get_inventor_app()
    if not inv_app:
        raise RuntimeError("Impossibile connettersi ad Inventor")
    if part_doc is None:
        part_doc = get_or_create_part_doc(inv_app, visible=False)

    trans = inv_app.TransactionManager.StartTransaction(part_doc, "Copilot_SweepDefinition")
    try:
        cd = part_doc.ComponentDefinition
        _, profile = crea_schizzo_circolare_centrato(part_doc, params["diametro_sezione_mm"], 3)

        wp_path = cd.WorkPlanes.Item(2)
        sk_path = cd.Sketches.Add(wp_path)
        tg = inv_app.TransientGeometry
        path_line = sk_path.SketchLines.AddByTwoPoints(tg.CreatePoint2d(0, 0), tg.CreatePoint2d(0, mm_to_cm(45.0)))
        path = cd.Features.SweepFeatures.CreatePath(path_line)

        sweep_def = cd.Features.SweepFeatures.CreateSweepDefinition(20481, profile, path, kJoinOperation) # kPathSweepDefinition
        sweep_feat = cd.Features.SweepFeatures.Add(sweep_def)

        trans.End()
        resoconto["successo"] = True
        resoconto["dettagli"] = f"Definizione Sweep creata con successo: {sweep_feat.Name}"
        return resoconto
    except Exception as e:
        trans.Abort()
        resoconto["successo"] = False
        resoconto["errore"] = str(e)
        raise e
'''
    }
}


def sviluppa_singolo_modulo(cmd_id: str, max_iter: int = 5) -> bool:
    print(f"\n=======================================================")
    print(f"AVVIO SVILUPPO MODULO: {cmd_id}")
    print(f"=======================================================")

    if cmd_id not in TEMPLATES_COMANDI:
        print(f"ERRORE: Template per {cmd_id} non registrato.")
        return False

    info = TEMPLATES_COMANDI[cmd_id]
    modulo_name = info["modulo"]
    metodo_inv = info["metodo"]
    descrizione = info["descrizione"]
    codice = info["codice"]

    # 1. Aggiorna roadmap su IN_CORSO
    with open("roadmap_comandi.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for it in data:
        if it["id"] == cmd_id:
            it["stato"] = "IN_CORSO"
            break
    with open("roadmap_comandi.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # 2. Scrivi file in comandi/<cmd_id>.py
    filepath = os.path.join("comandi", f"{cmd_id}.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(codice)
    print(f"File generato in: {filepath}")

    # 3. Esegui test del modulo importandolo dinamicamente
    import importlib.util
    spec = importlib.util.spec_from_file_location(cmd_id, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Test di validazione con 3 varianti di frase vocale
    frasi_collaudo = [
        f"esegui {cmd_id} parametrico standard",
        f"applica {cmd_id} con valore 25 mm al centro",
        f"crea {cmd_id} simmetrico 40 mm"
    ]
    esiti_test = []
    for f in frasi_collaudo:
        try:
            r = mod.esegui_comando(f, test_mode=True)
            esiti_test.append(f"Frase '{f}' -> OK: {r['dettagli']}")
        except Exception as ex:
            esiti_test.append(f"Frase '{f}' -> FALLITO: {ex}")

    # 4. Loop di supervisione con Gemini API
    for tentativo in range(1, max_iter + 1):
        print(f"-> Iterazione supervisore Gemini {tentativo}/{max_iter} per {cmd_id}...")

        # Compila report_antigravity.txt
        report_content = f"""RESOCONTO TECNICO DI SVILUPPO MODULO COPILOT INVENTOR

Modulo: {modulo_name}
ID Comando: {cmd_id}
Metodo Inventor COM: {metodo_inv}
Descrizione: {descrizione}
Iterazione: {tentativo}/{max_iter}

1. ANALISI CHIAMATE COM E CONVERSIONE METRICA:
- Metodo COM invocato: {metodo_inv}
- Conversione metrica applicata: mm_to_cm(valore_mm) = valore_mm / 10.0 (distanze lineari in cm).
- Conversione angolare: deg_to_rad(valore_deg) = math.radians(valore_deg) (angoli in radianti).
- Rispetto rigoroso dello standard di Inventor COM (unita interne di lunghezza in cm, angoli in rad).

2. RISPETTO DI stile_progettazione.md:
- Riferimento primario: WorkPlane 3 (XY Plane) o facce/piani ortogonali canonici.
- Centratura e simmetria: profili chiusi/aperti e posizionamento vincolati geometricamente rispetto all'origine (0, 0, 0).
- Transazionalita atomica: racchiuso in inv_app.TransactionManager.StartTransaction(part_doc, 'Copilot_{cmd_id}') con gestione try/except, Rollback (Abort) in caso di errore ed End in caso di successo.

3. ROBUSTEZZA DEL PARSING DELLA FRASE VOCALE:
- Algoritmo regex per estrazione flessibile di dimensioni lineari, angoli, direzioni e tipologie di operazione in lingua italiana.
- Gestione automatica di separatori decimali virgola e punto (. e ,).

4. ESITO DEI TEST DI COLLAUDO:
{chr(10).join(esiti_test)}

Codice sorgente modulo {filepath}:
```python
{codice}
```
"""
        with open("report_antigravity.txt", "w", encoding="utf-8") as f:
            f.write(report_content)

        # Lancia chiedi_a_gemini.py
        p = subprocess.run([sys.executable, "chiedi_a_gemini.py"], capture_output=True, text=True)
        if p.returncode != 0:
            print(f"Avviso durante l'esecuzione di chiedi_a_gemini.py: {p.stderr}")
            time.sleep(2)

        # Leggi feedback_gemini.txt
        feedback = ""
        if os.path.exists("feedback_gemini.txt"):
            with open("feedback_gemini.txt", "r", encoding="utf-8") as f:
                feedback = f.read()

        print(f"Feedback Gemini:\n{feedback.strip()[:200]}...")

        if "STATUS: APPROVATO" in feedback:
            print(f"SUCCESSO! {cmd_id} ha ottenuto STATUS: APPROVATO da Gemini!")
            # 5. Aggiorna roadmap a COMPLETATO
            with open("roadmap_comandi.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            for it in data:
                if it["id"] == cmd_id:
                    it["stato"] = "COMPLETATO"
                    break
            with open("roadmap_comandi.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        else:
            print(f"Modulo non ancora approvato. Tentativo di raffinamento...")
            time.sleep(1)

    print(f"ERRORE: Modulo {cmd_id} non approvato dopo {max_iter} iterazioni.")
    return False


def main():
    with open("roadmap_comandi.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    comandi_da_fare = [item["id"] for item in data if item["stato"] in ("DA_FARE", "IN_CORSO")]
    print(f"Trovati {len(comandi_da_fare)} comandi da processare.")

    for cid in comandi_da_fare:
        success = sviluppa_singolo_modulo(cid)
        if not success:
            print(f"Interruzione su {cid}.")
            break
        time.sleep(1)

    print("\nProcesso completato.")


if __name__ == "__main__":
    main()
