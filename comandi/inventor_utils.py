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


def get_active_selection(part_doc):
    """
    Rileva gli oggetti attualmente selezionati dall'utente nell'interfaccia di Inventor (SelectSet).
    Restituisce un dizionario con liste separate per facce, spigoli e punti.
    """
    selected = {"faces": [], "edges": [], "vertices": []}
    if not part_doc:
        return selected
    try:
        ss = part_doc.SelectSet
        for i in range(1, ss.Count + 1):
            item = ss.Item(i)
            # Riconoscimento tipo entita COM Inventor
            if hasattr(item, "SurfaceType") or hasattr(item, "FaceType") or hasattr(item, "TangentFaces"):
                selected["faces"].append(item)
            elif hasattr(item, "CurveType") or hasattr(item, "StartVertex"):
                selected["edges"].append(item)
            elif hasattr(item, "Point"):
                selected["vertices"].append(item)
    except Exception:
        pass
    return selected


def find_face_by_direction(body, direction_name: str = "top"):
    """
    Individua nel corpo solido la faccia piana che corrisponde alla direzione semantica indicata.
    Valori supportati:
    - 'top' / 'superiore' / 'alto' / 'sopra' (+Z)
    - 'bottom' / 'inferiore' / 'basso' / 'sotto' (-Z)
    - 'front' / 'frontale' / 'davanti' / 'anteriore' (-Y)
    - 'back' / 'posteriore' / 'dietro' (+Y)
    - 'right' / 'destra' / 'destro' (+X)
    - 'left' / 'sinistra' / 'sinistro' (-X)
    """
    d = direction_name.lower().strip()
    target_vector = (0.0, 0.0, 1.0) # default top (+Z)
    
    if any(k in d for k in ["bottom", "inferiore", "basso", "sotto"]):
        target_vector = (0.0, 0.0, -1.0)
    elif any(k in d for k in ["front", "frontale", "davanti", "anteriore"]):
        target_vector = (0.0, -1.0, 0.0)
    elif any(k in d for k in ["back", "posteriore", "dietro"]):
        target_vector = (0.0, 1.0, 0.0)
    elif any(k in d for k in ["right", "destra", "destro"]):
        target_vector = (1.0, 0.0, 0.0)
    elif any(k in d for k in ["left", "sinistra", "sinistro"]):
        target_vector = (-1.0, 0.0, 0.0)
    elif any(k in d for k in ["top", "superiore", "alto", "sopra"]):
        target_vector = (0.0, 0.0, 1.0)

    best_face = None
    best_dot = -2.0

    for i in range(1, body.Faces.Count + 1):
        f = body.Faces.Item(i)
        if hasattr(f.Geometry, "Normal"):
            n = f.Geometry.Normal
            dot = (n.X * target_vector[0]) + (n.Y * target_vector[1]) + (n.Z * target_vector[2])
            if dot > best_dot:
                best_dot = dot
                best_face = f

    if best_face is None or best_dot < 0.5:
        # Fallback alla prima faccia o faccia con Z massimo
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, "Normal") and abs(f.Geometry.Normal.Z - 1.0) < 0.2:
                return f
        return body.Faces.Item(1)

    return best_face


def get_face_edges_by_direction(face):
    """
    Categorizza gli spigoli di una faccia piana rispetto ai riferimenti orientati:
    'sinistro' / 'destro', 'inferiore' / 'superiore' (oppure 'fondo' / 'alto').
    Ritorna un dizionario con gli spigoli indicizzati per chiave semantica.
    """
    edges_info = []
    normal_z = 1.0
    if hasattr(face.Geometry, "Normal"):
        normal_z = abs(face.Geometry.Normal.Z)

    for i in range(1, face.Edges.Count + 1):
        e = face.Edges.Item(i)
        try:
            p1 = e.StartVertex.Point
            p2 = e.EndVertex.Point
            mid_x = (p1.X + p2.X) / 2.0
            mid_y = (p1.Y + p2.Y) / 2.0
            mid_z = (p1.Z + p2.Z) / 2.0
            
            # Se la faccia e principalmente sul piano XY (normale Z)
            if normal_z > 0.5:
                coord_u = mid_x  # asse orizzontale
                coord_v = mid_y  # asse verticale
                span_u = abs(p1.X - p2.X)
                span_v = abs(p1.Y - p2.Y)
            else:
                # Altrimenti per facce frontali o laterali usa X e Z
                coord_u = mid_x
                coord_v = mid_z
                span_u = abs(p1.X - p2.X)
                span_v = abs(p1.Z - p2.Z)

            edges_info.append({
                "edge": e,
                "u": coord_u,
                "v": coord_v,
                "span_u": span_u,
                "span_v": span_v
            })
        except Exception:
            pass

    if not edges_info:
        return {}

    # Trova i bordi verticali (lungo v, quindi span_v > span_u) con min u (sinistra) e max u (destra)
    # e bordi orizzontali (lungo u, quindi span_u > span_v) con min v (basso/inferiore) e max v (alto/superiore)
    edges_by_u = sorted(edges_info, key=lambda x: x["u"])
    edges_by_v = sorted(edges_info, key=lambda x: x["v"])

    edge_left = edges_by_u[0]["edge"]
    edge_right = edges_by_u[-1]["edge"]
    edge_bottom = edges_by_v[0]["edge"]
    edge_top = edges_by_v[-1]["edge"]

    return {
        "sinistro": edge_left,
        "sinistra": edge_left,
        "left": edge_left,
        "destro": edge_right,
        "destra": edge_right,
        "right": edge_right,
        "inferiore": edge_bottom,
        "basso": edge_bottom,
        "fondo": edge_bottom,
        "bottom": edge_bottom,
        "frontale": edge_bottom,
        "superiore": edge_top,
        "alto": edge_top,
        "top": edge_top,
        "posteriore": edge_top
    }


def create_smart_hole_placement(inv_app, part_doc, params):
    """
    Costruisce e restituisce il corretto HolePlacementDefinition di Inventor:
    1. LinearPlacementDefinition: se sono specificati riferimenti a bordi/spigoli e relative quote;
    2. ConcentricPlacementDefinition: se e richiesta concentricita e vi e un bordo circolare;
    3. SketchPlacementDefinition: se sono specificate coordinate assolute X, Y o posizionamento 'al centro'.
    """
    cd = part_doc.ComponentDefinition
    body = cd.SurfaceBodies.Item(1)
    
    # 1. Individuazione della Faccia di appoggio
    target_face = None
    
    # Priorita A: Faccia attualmente selezionata a video dall'utente
    sel = get_active_selection(part_doc)
    if sel["faces"]:
        target_face = sel["faces"][0]
        
    # Priorita B: Faccia specificata semanticamente nella frase (es. "sulla faccia frontale", "superiore")
    if target_face is None and params.get("faccia_target"):
        target_face = find_face_by_direction(body, params["faccia_target"])
        
    # Priorita C: Default faccia superiore (+Z)
    if target_face is None:
        target_face = find_face_by_direction(body, "top")

    hole_features = cd.Features.HoleFeatures

    # --- STRATEGIA 1: POSIZIONAMENTO LINEARE DA SPIGOLI (LinearPlacement) ---
    bordo1 = params.get("bordo1")
    dist1_mm = params.get("distanza1_mm")
    bordo2 = params.get("bordo2")
    dist2_mm = params.get("distanza2_mm")

    if bordo1 and dist1_mm is not None and bordo2 and dist2_mm is not None:
        edges_map = get_face_edges_by_direction(target_face)
        ref_edge1 = edges_map.get(bordo1)
        ref_edge2 = edges_map.get(bordo2)

        if ref_edge1 and ref_edge2 and ref_edge1 != ref_edge2:
            dist1_cm = mm_to_cm(dist1_mm)
            dist2_cm = mm_to_cm(dist2_mm)
            try:
                placement_def = hole_features.CreateLinearPlacementDefinition(
                    target_face, ref_edge1, dist1_cm, ref_edge2, dist2_cm
                )
                return placement_def, f"Posizionamento lineare da bordi: {bordo1}={dist1_mm}mm, {bordo2}={dist2_mm}mm"
            except Exception:
                pass

    # --- STRATEGIA 2: POSIZIONAMENTO CONCENTRICO (ConcentricPlacement) ---
    if params.get("concentrico"):
        concentric_edge = None
        # Se l'utente ha selezionato uno spigolo circolare
        if sel["edges"]:
            for e in sel["edges"]:
                if hasattr(e, "CurveType") and e.CurveType in (5123, 5124): # Circle/Arc
                    concentric_edge = e
                    break
        if concentric_edge is None:
            # Cerca il primo spigolo circolare sulla faccia
            for i in range(1, target_face.Edges.Count + 1):
                e = target_face.Edges.Item(i)
                if hasattr(e, "CurveType") and e.CurveType in (5123, 5124):
                    concentric_edge = e
                    break
        if concentric_edge:
            try:
                placement_def = hole_features.CreateConcentricPlacementDefinition(target_face, concentric_edge)
                return placement_def, "Posizionamento concentrico a spigolo circolare"
            except Exception:
                pass

    # --- STRATEGIA 3: POSIZIONAMENTO SU SCHIZZO (SketchPlacementDefinition) ---
    # Usato per coordinate X, Y o 'al centro' (0, 0)
    pos_x_mm = params.get("pos_x_mm", 0.0)
    pos_y_mm = params.get("pos_y_mm", 0.0)
    al_centro = params.get("al_centro", False) or (abs(pos_x_mm) < 1e-6 and abs(pos_y_mm) < 1e-6)

    sk = cd.Sketches.Add(target_face)
    tg = inv_app.TransientGeometry

    pos_x_cm = mm_to_cm(pos_x_mm)
    pos_y_cm = mm_to_cm(pos_y_mm)
    sp = sk.SketchPoints.Add(tg.CreatePoint2d(pos_x_cm, pos_y_cm))

    if al_centro:
        try:
            sk.GeometricConstraints.AddCoincident(sk.OriginPoint, sp)
        except Exception:
            pass
        msg = "Posizionamento al centro della faccia (coincidente con origine)"
    else:
        # Aggiunta quote parametriche grafiche rispetto all'origine dello schizzo
        try:
            proj_origin = sk.AddByProjectingEntity(cd.WorkPoints.Item(1))
            # Quota orizzontale X
            tp_x = tg.CreatePoint2d(pos_x_cm / 2.0, pos_y_cm + 1.0)
            sk.DimensionConstraints.AddTwoPointDistance(proj_origin, sp, 19203, tp_x, False)
            # Quota verticale Y
            tp_y = tg.CreatePoint2d(pos_x_cm + 1.0, pos_y_cm / 2.0)
            sk.DimensionConstraints.AddTwoPointDistance(proj_origin, sp, 19203, tp_y, False)
        except Exception:
            pass
        msg = f"Posizionamento su schizzo a coordinate X={pos_x_mm} mm, Y={pos_y_mm} mm"

    try:
        sk.Solve()
    except Exception:
        pass

    coll = inv_app.TransientObjects.CreateObjectCollection()
    coll.Add(sp)
    placement_def = hole_features.CreateSketchPlacementDefinition(coll)
    return placement_def, msg


def analizza_posizionamento_foro(frase: str) -> dict:
    """
    Estrae le informazioni di posizionamento spaziale del foro:
    - Riferimento a spigoli/bordi con distanze (Linear Placement)
    - Coordinate assolute o relative X, Y
    - Riferimento concentrico a spigoli circolari/raccordi
    - Faccia target semantica o selezionata
    """
    f = frase.lower().strip()
    res = {
        "bordo1": None,
        "distanza1_mm": None,
        "bordo2": None,
        "distanza2_mm": None,
        "pos_x_mm": 0.0,
        "pos_y_mm": 0.0,
        "al_centro": "centro" in f,
        "concentrico": "concentrico" in f or "raccordo" in f,
        "faccia_target": None
    }

    # 1. Rilevamento faccia target
    for orient in ["superiore", "inferiore", "frontale", "posteriore", "destra", "destro", "sinistra", "sinistro"]:
        if f"faccia {orient}" in f or f"sul {orient}" in f or f"sulla {orient}" in f:
            res["faccia_target"] = orient
            break

    # 2. Rilevamento spigoli/bordi e relative distanze lineari
    edges_found = []
    # Pattern 1: 'a 20 mm da sinistra' o '20 mm dal bordo sinistro'
    pat1 = re.finditer(r'(?:a\s+|distante\s+)?(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)?\s*(?:da|dal|dalla|dallo|rispetto\s+a(?:l|lla)?)\s*(?:bordo\s+|spigolo\s+)?(sinistro|sinistra|destro|destra|inferiore|basso|sotto|fondo|superiore|alto|sopra|posteriore|frontale)\b', f)
    for m in pat1:
        val = float(m.group(1).replace(',', '.'))
        b = m.group(2)
        edges_found.append((b, val, m.start()))

    # Pattern 2: 'da sinistra 20 mm' o 'dal bordo sinistro a 20 mm'
    pat2 = re.finditer(r'(?:da|dal|dalla|rispetto\s+a(?:l|lla)?)\s*(?:bordo\s+|spigolo\s+)?(sinistro|sinistra|destro|destra|inferiore|basso|sotto|fondo|superiore|alto|sopra|posteriore|frontale)\s*(?:a|di|distante|:=)?\s*(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)?\b', f)
    for m in pat2:
        b = m.group(1)
        val = float(m.group(2).replace(',', '.'))
        edges_found.append((b, val, m.start()))

    # Eliminiamo duplicati mantenendo l'ordine di comparsa
    unique_edges = []
    seen = set()
    for b, val, pos in sorted(edges_found, key=lambda x: x[2]):
        if b not in seen:
            seen.add(b)
            unique_edges.append((b, val))

    if len(unique_edges) >= 2:
        res["bordo1"] = unique_edges[0][0]
        res["distanza1_mm"] = unique_edges[0][1]
        res["bordo2"] = unique_edges[1][0]
        res["distanza2_mm"] = unique_edges[1][1]
        res["al_centro"] = False

    # 3. Coordinate esplicite X e Y
    match_x = re.search(r'\bx\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)
    match_y = re.search(r'\by\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)\b', f)
    if match_x:
        res["pos_x_mm"] = float(match_x.group(1).replace(',', '.'))
        res["al_centro"] = False
    if match_y:
        res["pos_y_mm"] = float(match_y.group(1).replace(',', '.'))
        res["al_centro"] = False

    return res


def estrai_diametro_foro(frase: str, default_mm: float = 10.0) -> float:
    """Estrae in modo affidabile il diametro o la misura metrica (es. M10, diametro 12, foro da 14)."""
    f = frase.lower().strip()
    m_m = re.search(r'\bm(\d+(?:[.,]\d+)?)\b', f)
    if m_m:
        return float(m_m.group(1).replace(',', '.'))
    m = re.search(r'(?:diametro|d)\s*(?:di|da|a)?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if m:
        return float(m.group(1).replace(',', '.'))
    m2 = re.search(r'\bforo\s+(?:da|di)?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if m2:
        return float(m2.group(1).replace(',', '.'))
    return float(default_mm)
