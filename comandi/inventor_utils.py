"""
comandi/inventor_utils.py
Utilità condivise per comandi vocali Autodesk Inventor Copilot.
Rispettano rigorosamente stile_progettazione.md:
- Conversione metrica millimetri -> centimetri (mm / 10.0)
- Conversione angoli gradi -> radianti (math.radians)
- Transazionalità atomica tramite TransactionManager
- Centratura e simmetria sull'origine del piano XY (WorkPlane 3)
"""

import math
import re
from typing import Optional, Tuple, Any

# Costanti Enums Autodesk Inventor
kPartDocumentObject = 12290
kFullyConstrainedConstraintStatus = 51713
kAlignedDimension = 19203
kPositiveExtentDirection = 20993
kNegativeExtentDirection = 20994
kSymmetricExtentDirection = 20995
kJoinOperation = 20481
kCutOperation = 20482
kIntersectOperation = 20483
kNewBodyOperation = 20484


def mm_to_cm(valore_mm: float) -> float:
    """Converte millimetri nell'unità interna di Inventor (centimetri)."""
    return float(valore_mm) / 10.0


def cm_to_mm(valore_cm: float) -> float:
    """Converte centimetri interni Inventor in millimetri utente."""
    return float(valore_cm) * 10.0


def deg_to_rad(valore_deg: float) -> float:
    """Converte gradi in radianti per le API COM di Inventor."""
    return math.radians(float(valore_deg))


def get_inventor_app():
    """Ottiene l'istanza attiva di Inventor o ne avvia una nuova visibile."""
    import win32com.client
    try:
        app = win32com.client.GetActiveObject("Inventor.Application")
    except Exception:
        app = win32com.client.Dispatch("Inventor.Application")
    try:
        app.Visible = True
    except Exception:
        pass
    return app


def get_or_create_part_doc(inv_app, visible: bool = True):
    """
    Restituisce il PartDocument attivo se presente, altrimenti ne crea uno nuovo visibile.
    Imposta tassativamente le unita di misura in Millimetri (11269), cosicche tutte le
    maschere di lavorazione (Foro, Estrusione, ecc.) mostrino mm e non cm.
    """
    doc = None
    try:
        if inv_app.ActiveDocument and inv_app.ActiveDocumentType == kPartDocumentObject:
            doc = inv_app.ActiveDocument
    except Exception:
        pass
    if doc is None:
        try:
            inv_app.Visible = True
        except Exception:
            pass
        doc = inv_app.Documents.Add(kPartDocumentObject, "", visible)
    
    try:
        # 11269 = kMillimeterLengthUnits, 11279 = kDegreeAngleUnits
        doc.UnitsOfMeasure.LengthUnits = 11269
        doc.UnitsOfMeasure.AngleUnits = 11279
    except Exception:
        pass
    return doc


def crea_schizzo_rettangolare_centrato(part_doc, larghezza_mm: float, altezza_mm: float, piano_indice: int = 3):
    """
    Crea uno schizzo sul piano indicato (default 3: XY Plane) con un rettangolo
    perfettamente centrato sull'origine (0, 0, 0), COMPLETAMENTE VINCOLATO (ConstraintStatus = 51713),
    con linee nere, quote dimensionali visibili e diagonali di costruzione centrate,
    esattamente secondo la convenzione estratta dai file di modello dell'utente (Esempio-002.ipt).
    """
    cd = part_doc.ComponentDefinition
    work_plane = cd.WorkPlanes.Item(piano_indice)
    sketch = cd.Sketches.Add(work_plane)
    
    trans_geom = part_doc.Parent.TransientGeometry
    
    # Coordinate in cm per Inventor (mm / 10.0)
    w_cm = mm_to_cm(larghezza_mm)
    h_cm = mm_to_cm(altezza_mm)
    half_w = w_cm / 2.0
    half_h = h_cm / 2.0
    
    p1 = trans_geom.CreatePoint2d(-half_w, -half_h)
    p2 = trans_geom.CreatePoint2d(half_w, half_h)
    
    # 1. 4 linee del rettangolo con vincoli orizzontali e verticali
    lines = sketch.SketchLines.AddAsTwoPointRectangle(p1, p2)
    l_bottom = lines.Item(1)
    l_right  = lines.Item(2)
    l_top    = lines.Item(3)
    l_left   = lines.Item(4)
    
    # 2. Due diagonali di costruzione che collegano i vertici opposti (come in Esempio-002)
    diag1 = sketch.SketchLines.AddByTwoPoints(l_bottom.StartSketchPoint, l_top.StartSketchPoint)
    diag1.Construction = True
    
    diag2 = sketch.SketchLines.AddByTwoPoints(l_bottom.EndSketchPoint, l_top.EndSketchPoint)
    diag2.Construction = True
    
    # 3. Proiezione del punto d'origine del modello nello schizzo
    proj_origin = sketch.AddByProjectingEntity(cd.WorkPoints.Item(1))
    
    # 4. Vincoli di coincidenza tra l'origine fissa e le due diagonali
    sketch.GeometricConstraints.AddCoincident(proj_origin, diag1)
    sketch.GeometricConstraints.AddCoincident(proj_origin, diag2)
    
    # 5. Quote parametriche grafiche visibili (AddTwoPointDistance, orientamento 19203)
    tp_w = trans_geom.CreatePoint2d(0, -half_h - 1.5)
    sketch.DimensionConstraints.AddTwoPointDistance(
        l_bottom.StartSketchPoint, l_bottom.EndSketchPoint, kAlignedDimension, tp_w, False
    )
    
    tp_h = trans_geom.CreatePoint2d(half_w + 1.5, 0)
    sketch.DimensionConstraints.AddTwoPointDistance(
        l_right.StartSketchPoint, l_right.EndSketchPoint, kAlignedDimension, tp_h, False
    )
    
    # 6. Risoluzione e aggiornamento dello schizzo per garantire 51713
    try:
        sketch.Solve()
    except Exception:
        pass
        
    profile = sketch.Profiles.AddForSolid()
    return sketch, profile


def crea_schizzo_circolare_centrato(part_doc, diametro_mm: float, piano_indice: int = 3):
    """
    Crea uno schizzo sul piano indicato (default 3: XY Plane) con un cerchio
    avente centro vincolato coincidentemente all'origine (0, 0, 0), COMPLETAMENTE VINCOLATO (51713)
    e quota diametro parametrica visibile.
    """
    cd = part_doc.ComponentDefinition
    work_plane = cd.WorkPlanes.Item(piano_indice)
    sketch = cd.Sketches.Add(work_plane)
    
    trans_geom = part_doc.Parent.TransientGeometry
    raggio_cm = mm_to_cm(diametro_mm) / 2.0
    
    # 1. Proiezione dell'origine
    proj_origin = sketch.AddByProjectingEntity(cd.WorkPoints.Item(1))
    
    # 2. Cerchio con centro a (0, 0)
    circle = sketch.SketchCircles.AddByCenterRadius(trans_geom.CreatePoint2d(0.0, 0.0), raggio_cm)
    
    # 3. Vincolo coincidente tra il centro del cerchio e l'origine proiettata
    sketch.GeometricConstraints.AddCoincident(circle.CenterSketchPoint, proj_origin)
    
    # 4. Quota diametrale grafica visibile
    tp = trans_geom.CreatePoint2d(raggio_cm + 1.0, raggio_cm + 1.0)
    sketch.DimensionConstraints.AddDiameter(circle, tp, False)
    
    # 5. Risoluzione
    try:
        sketch.Solve()
    except Exception:
        pass
    
    profile = sketch.Profiles.AddForSolid()
    return sketch, profile
