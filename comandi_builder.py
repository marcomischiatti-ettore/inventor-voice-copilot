"""
comandi_builder.py
Generatore e repository dei moduli CAD vocali per Autodesk Inventor Copilot.
Ogni modulo rispetta rigorosamente:
1. stile_progettazione.md (cm = mm/10, rad per angoli, simmetria origine, transazioni atomiche)
2. Parsing vocale avanzato in italiano
3. Modalità test e modalità COM live
"""

import math

MODULI_SORGENTI = {}

# -------------------------------------------------------------
# 6. hole_drilled_through_all
# -------------------------------------------------------------
MODULI_SORGENTI["hole_drilled_through_all"] = '''"""
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


def esegui_foro_passante(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
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

# -------------------------------------------------------------
# 7. hole_cbore_distance
# -------------------------------------------------------------
MODULI_SORGENTI["hole_cbore_distance"] = '''"""
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


def esegui_foro_lamato(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
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

# -------------------------------------------------------------
# 8. hole_csink_distance
# -------------------------------------------------------------
MODULI_SORGENTI["hole_csink_distance"] = '''"""
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


def esegui_foro_svasato(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
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

# -------------------------------------------------------------
# 9. hole_definition
# -------------------------------------------------------------
MODULI_SORGENTI["hole_definition"] = '''"""
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
    filettato = "filettat" in f or "maschiat" in f
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
        "filettato": filettato,
        "passante": passante,
        "frase_originale": frase
    }


def esegui_definizione_foratura(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
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

# -------------------------------------------------------------
# 10. thread_standard
# -------------------------------------------------------------
MODULI_SORGENTI["thread_standard"] = '''"""
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


def esegui_filettatura(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
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
        # Creiamo un perno cilindrico simmetrico se non ci sono facce cilindriche
        cyl_face = None
        if cd.SurfaceBodies.Count > 0:
            body = cd.SurfaceBodies.Item(1)
            for i in range(1, body.Faces.Count + 1):
                fc = body.Faces.Item(i)
                if fc.SurfaceType in (5635, 5636): # kCylinderSurface
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

print("Moduli base compilati con successo in comandi_builder.")
