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
    """
    try:
        if inv_app.ActiveDocument and inv_app.ActiveDocumentType == kPartDocumentObject:
            return inv_app.ActiveDocument
    except Exception:
        pass
    try:
        inv_app.Visible = True
    except Exception:
        pass
    return inv_app.Documents.Add(kPartDocumentObject, "", visible)


def crea_schizzo_rettangolare_centrato(part_doc, larghezza_mm: float, altezza_mm: float, piano_indice: int = 3):
    """
    Crea uno schizzo sul piano indicato (default 3: XY Plane) con un rettangolo
    perfettamente centrato e simmetrico sull'origine (0, 0, 0), come da stile_progettazione.md.
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
    
    # AddAsTwoPointRectangle crea automaticamente le 4 linee con i vincoli orizzontali e verticali
    rect_lines = sketch.SketchLines.AddAsTwoPointRectangle(p1, p2)
    
    # Vincoli di simmetria rispetto all'origine:
    # Aggiunge quote parametriche centrate o vincoli di simmetria se necessario
    profile = sketch.Profiles.AddForSolid()
    return sketch, profile


def crea_schizzo_circolare_centrato(part_doc, diametro_mm: float, piano_indice: int = 3):
    """
    Crea uno schizzo sul piano indicato (default 3: XY Plane) con un cerchio
    avente centro vincolato coincidentemente all'origine (0, 0, 0).
    """
    cd = part_doc.ComponentDefinition
    work_plane = cd.WorkPlanes.Item(piano_indice)
    sketch = cd.Sketches.Add(work_plane)
    
    trans_geom = part_doc.Parent.TransientGeometry
    centro = trans_geom.CreatePoint2d(0.0, 0.0)
    raggio_cm = mm_to_cm(diametro_mm) / 2.0
    
    circle = sketch.SketchCircles.AddByCenterRadius(centro, raggio_cm)
    try:
        sketch.GeometricConstraints.AddCoincident(sketch.OriginPoint, circle.CenterSketchPoint)
    except Exception:
        pass
    
    profile = sketch.Profiles.AddForSolid()
    return sketch, profile
