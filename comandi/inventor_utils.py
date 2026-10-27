"""
comandi/inventor_utils.py
Utilità condivise per comandi vocali Autodesk Inventor Copilot.
Rispettano rigorosamente stile_progettazione.md:
- Conversione metrica millimetri -> centimetri (mm / 10.0)
- Conversione angoli gradi -> radianti (math.radians)
- Transazionalità atomica tramite TransactionManager
- Centratura e simmetria sull'origine del piano XY (WorkPlane 3)
- Normalizzazione vocale per abbreviazioni d'officina (diam., d., ø, sx, dx, sup, inf)
- Smart Placement su bordi/spigoli con quote visibili e supporto selezione interattiva (SelectSet)
"""

import math
import re
from typing import Optional, Tuple, Any, Dict, List

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


def normalizza_frase(frase: str) -> str:
    """Normalizza abbreviazioni frequenti in ambito CAD d'officina prima del parsing."""
    f = frase.lower().strip()
    f = re.sub(r'\bdiam\.\s*', 'diametro ', f)
    f = re.sub(r'\bdiam\b', 'diametro', f)
    f = re.sub(r'\bd\.\s*', 'diametro ', f)
    f = re.sub(r'\bø\s*', 'diametro ', f)
    f = re.sub(r'\bfi\s*', 'diametro ', f)
    f = re.sub(r'\bsx\b', 'sinistra', f)
    f = re.sub(r'\bdx\b', 'destra', f)
    f = re.sub(r'\bsup\b', 'superiore', f)
    f = re.sub(r'\binf\b', 'inferiore', f)
    # Stacca numeri da mm/cm (es. 20mm -> 20 mm)
    f = re.sub(r'(\d+)(mm|millimetri)\b', r'\1 \2', f)
    f = re.sub(r'(\d+)(cm|centimetri)\b', r'\1 \2', f)
    # Normalizzazione preposizioni articolate d'officina per riferimenti bordi/spigoli
    f = re.sub(r'\bdall[\'\s]?alto\b', 'da alto', f)
    f = re.sub(r'\bdall[\'\s]?altra\b', 'da altra', f)
    f = re.sub(r'\bdall[\'\s]?inizio\b', 'da inizio', f)
    f = re.sub(r'\bdal[\s]?fondo\b', 'da fondo', f)
    f = re.sub(r'\bdal[\s]?basso\b', 'da basso', f)
    f = re.sub(r'\bdal[\s]?sotto\b', 'da sotto', f)
    f = re.sub(r'\bdal[\s]?sopra\b', 'da sopra', f)
    f = re.sub(r'\bdal[\s]?sinistro\b', 'da sinistro', f)
    f = re.sub(r'\bdal[\s]?destro\b', 'da destro', f)
    f = re.sub(r'\bdalla[\s]?sinistra\b', 'da sinistra', f)
    f = re.sub(r'\bdalla[\s]?destra\b', 'da destra', f)
    return f


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
        doc.UnitsOfMeasure.LengthUnits = 11269
        doc.UnitsOfMeasure.AngleUnits = 11279
    except Exception:
        pass
    return doc


def crea_schizzo_rettangolare_centrato(part_doc, larghezza_mm: float, altezza_mm: float, piano_indice: int = 3):
    """
    Crea uno schizzo sul piano indicato (default 3: XY Plane) con un rettangolo
    perfettamente centrato sull'origine (0, 0, 0), COMPLETAMENTE VINCOLATO (51713),
    con diagonali di costruzione e quote parametriche grafiche visibili.
    """
    cd = part_doc.ComponentDefinition
    work_plane = cd.WorkPlanes.Item(piano_indice)
    sketch = cd.Sketches.Add(work_plane)
    
    trans_geom = part_doc.Parent.TransientGeometry
    w_cm = mm_to_cm(larghezza_mm)
    h_cm = mm_to_cm(altezza_mm)
    half_w = w_cm / 2.0
    half_h = h_cm / 2.0
    
    p1 = trans_geom.CreatePoint2d(-half_w, -half_h)
    p2 = trans_geom.CreatePoint2d(half_w, half_h)
    
    lines = sketch.SketchLines.AddAsTwoPointRectangle(p1, p2)
    l_bottom = lines.Item(1)
    l_right  = lines.Item(2)
    l_top    = lines.Item(3)
    l_left   = lines.Item(4)
    
    diag1 = sketch.SketchLines.AddByTwoPoints(l_bottom.StartSketchPoint, l_top.StartSketchPoint)
    diag1.Construction = True
    
    diag2 = sketch.SketchLines.AddByTwoPoints(l_bottom.EndSketchPoint, l_top.EndSketchPoint)
    diag2.Construction = True
    
    proj_origin = sketch.AddByProjectingEntity(cd.WorkPoints.Item(1))
    sketch.GeometricConstraints.AddCoincident(proj_origin, diag1)
    sketch.GeometricConstraints.AddCoincident(proj_origin, diag2)
    
    tp_w = trans_geom.CreatePoint2d(0, -half_h - 1.5)
    sketch.DimensionConstraints.AddTwoPointDistance(
        l_bottom.StartSketchPoint, l_bottom.EndSketchPoint, kAlignedDimension, tp_w, False
    )
    
    tp_h = trans_geom.CreatePoint2d(half_w + 1.5, 0)
    sketch.DimensionConstraints.AddTwoPointDistance(
        l_right.StartSketchPoint, l_right.EndSketchPoint, kAlignedDimension, tp_h, False
    )
    
    try:
        sketch.Solve()
    except Exception:
        pass
        
    profile = sketch.Profiles.AddForSolid()
    return sketch, profile


def crea_schizzo_circolare_centrato(part_doc, diametro_mm: float, piano_indice: int = 3):
    """Crea uno schizzo con cerchio centrato sull'origine (0, 0) completamente vincolato."""
    cd = part_doc.ComponentDefinition
    work_plane = cd.WorkPlanes.Item(piano_indice)
    sketch = cd.Sketches.Add(work_plane)
    
    trans_geom = part_doc.Parent.TransientGeometry
    raggio_cm = mm_to_cm(diametro_mm) / 2.0
    
    proj_origin = sketch.AddByProjectingEntity(cd.WorkPoints.Item(1))
    circle = sketch.SketchCircles.AddByCenterRadius(trans_geom.CreatePoint2d(0.0, 0.0), raggio_cm)
    sketch.GeometricConstraints.AddCoincident(circle.CenterSketchPoint, proj_origin)
    
    tp = trans_geom.CreatePoint2d(raggio_cm + 1.0, raggio_cm + 1.0)
    sketch.DimensionConstraints.AddDiameter(circle, tp, False)
    
    try:
        sketch.Solve()
    except Exception:
        pass
    
    profile = sketch.Profiles.AddForSolid()
    return sketch, profile


def get_active_selection(part_doc):
    """Rileva gli oggetti attualmente selezionati dall'utente in Inventor (SelectSet)."""
    selected = {"faces": [], "edges": [], "vertices": []}
    if not part_doc:
        return selected
    try:
        ss = part_doc.SelectSet
        for i in range(1, ss.Count + 1):
            item = ss.Item(i)
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
    """Individua nel corpo solido la faccia piana che corrisponde alla direzione semantica indicata."""
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
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if hasattr(f.Geometry, "Normal") and abs(f.Geometry.Normal.Z - 1.0) < 0.2:
                return f
        return body.Faces.Item(1)

    return best_face


def get_face_edges_and_bounds(face):
    """
    Categorizza gli spigoli esterni e calcola i limiti cartesiani (min_u, max_u, min_v, max_v)
    della faccia piana, utilizzando il loop di confine primario per ignorare fori preesistenti.
    """
    edges_info = []
    normal_z = 1.0
    if hasattr(face.Geometry, "Normal"):
        normal_z = abs(face.Geometry.Normal.Z)

    # In Inventor, EdgeLoops.Item(1) è sempre il loop perimetrale esterno del solido
    edge_source = face.Edges
    try:
        if hasattr(face, "EdgeLoops") and face.EdgeLoops.Count >= 1:
            edge_source = face.EdgeLoops.Item(1).Edges
    except Exception:
        pass

    for i in range(1, edge_source.Count + 1):
        e = edge_source.Item(i)
        try:
            p1 = e.StartVertex.Point
            p2 = e.EndVertex.Point
            mid_x = (p1.X + p2.X) / 2.0
            mid_y = (p1.Y + p2.Y) / 2.0
            mid_z = (p1.Z + p2.Z) / 2.0
            
            if normal_z > 0.5:
                coord_u = mid_x
                coord_v = mid_y
                span_u = abs(p1.X - p2.X)
                span_v = abs(p1.Y - p2.Y)
            else:
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
        # Fallback conservativo su piastra standard 100x100
        return {}, -5.0, 5.0, -5.0, 5.0

    edges_by_u = sorted(edges_info, key=lambda x: x["u"])
    edges_by_v = sorted(edges_info, key=lambda x: x["v"])

    min_u = edges_by_u[0]["u"]
    max_u = edges_by_u[-1]["u"]
    min_v = edges_by_v[0]["v"]
    max_v = edges_by_v[-1]["v"]

    edge_left = edges_by_u[0]["edge"]
    edge_right = edges_by_u[-1]["edge"]
    edge_bottom = edges_by_v[0]["edge"]
    edge_top = edges_by_v[-1]["edge"]

    edges_map = {
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
        "posteriore": edge_top,
        "sopra": edge_top,
        "sotto": edge_bottom
    }

    return edges_map, min_u, max_u, min_v, max_v


def estrai_diametro_foro(frase: str, default_mm: float = 10.0) -> float:
    """Estrae in modo affidabile il diametro o la misura metrica (es. M10, diametro 12, foro da 14)."""
    f = normalizza_frase(frase)
    m_m = re.search(r'\bm(\d+(?:[.,]\d+)?)\b', f)
    if m_m:
        return float(m_m.group(1).replace(',', '.'))
    
    # Esplicito: diametro 12, d 12, foro da 12, foro 12
    m = re.search(r'(?:diametro|d)\s*(?:di|da|a)?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if m:
        return float(m.group(1).replace(',', '.'))
    
    m2 = re.search(r'\bforo\s+(?:passante\s+|cieco\s+)?(?:da|di)?\s*(\d+(?:[.,]\d+)?)(?:\s*(?:mm|millimetri))?', f)
    if m2:
        return float(m2.group(1).replace(',', '.'))
        
    return float(default_mm)


def analizza_posizionamento_foro(frase: str) -> dict:
    """Estrae le informazioni di posizionamento spaziale del foro con normalizzazione abbreviazioni."""
    f = normalizza_frase(frase)
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
    bordi_pattern = r'(sinistro|sinistra|destro|destra|inferiore|basso|sotto|fondo|superiore|alto|sopra|posteriore|frontale)'
    
    # Pattern 1: 'a 20 mm da sinistra' o '20 mm dal bordo sinistro'
    pat1 = re.finditer(rf'(?:a\s+|distante\s+)?(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)?\s*(?:da|dal|dalla|dallo|rispetto\s+a(?:l|lla)?)\s*(?:bordo\s+|spigolo\s+)?{bordi_pattern}\b', f)
    for m in pat1:
        val = float(m.group(1).replace(',', '.'))
        b = m.group(2)
        edges_found.append((b, val, m.start()))

    # Pattern 2: 'da sinistra 20 mm' o 'dal bordo sinistro a 20 mm'
    pat2 = re.finditer(rf'(?:da|dal|dalla|rispetto\s+a(?:l|lla)?)\s*(?:bordo\s+|spigolo\s+)?{bordi_pattern}\s*(?:a|di|distante|:=)?\s*(\d+(?:[.,]\d+)?)\s*(?:mm|millimetri)?\b', f)
    for m in pat2:
        b = m.group(1)
        val = float(m.group(2).replace(',', '.'))
        edges_found.append((b, val, m.start()))

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


def create_smart_hole_placement(inv_app, part_doc, params):
    """
    Costruisce e restituisce il corretto HolePlacementDefinition di Inventor:
    1. Se specificati riferimenti a bordi/spigoli con quote:
       Calcola le coordinate cartesiane esatte a partire dai limiti della faccia
       e posiziona il foro esattamente a quell'offset dai bordi!
    2. ConcentricPlacementDefinition: se e richiesta concentricita;
    3. SketchPlacementDefinition: per coordinate assolute X, Y o 'al centro'.
    """
    cd = part_doc.ComponentDefinition
    body = cd.SurfaceBodies.Item(1)
    
    # 1. Individuazione della Faccia di appoggio
    target_face = None
    
    # Priorità A: Faccia attualmente selezionata a video dall'utente
    sel = get_active_selection(part_doc)
    if sel["faces"]:
        target_face = sel["faces"][0]
        
    # Priorità B: Faccia specificata semanticamente nella frase
    if target_face is None and params.get("faccia_target"):
        target_face = find_face_by_direction(body, params["faccia_target"])
        
    # Priorità C: Default faccia superiore (+Z)
    if target_face is None:
        target_face = find_face_by_direction(body, "top")

    hole_features = cd.Features.HoleFeatures
    tg = inv_app.TransientGeometry

    # --- STRATEGIA 1: CONCENTRICA ---
    if params.get("concentrico"):
        concentric_edge = None
        if sel["edges"]:
            for e in sel["edges"]:
                if hasattr(e, "CurveType") and e.CurveType in (5123, 5124):
                    concentric_edge = e
                    break
        if concentric_edge is None:
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

    # --- CREAZIONE SCHIZZO SULLA FACCIA ---
    sk = cd.Sketches.Add(target_face)
    
    bordo1 = params.get("bordo1")
    dist1_mm = params.get("distanza1_mm")
    bordo2 = params.get("bordo2")
    dist2_mm = params.get("distanza2_mm")

    # --- STRATEGIA 2: POSIZIONAMENTO PARAMETRICO DA BORDI ---
    if bordo1 and dist1_mm is not None and bordo2 and dist2_mm is not None:
        edges_map, min_u, max_u, min_v, max_v = get_face_edges_and_bounds(target_face)
        dist1_cm = mm_to_cm(dist1_mm)
        dist2_cm = mm_to_cm(dist2_mm)

        target_x = 0.0
        target_y = 0.0

        # Asse determinato da bordo 1
        if bordo1 in ["sinistra", "sinistro", "left"]:
            target_x = min_u + dist1_cm
        elif bordo1 in ["destra", "destro", "right"]:
            target_x = max_u - dist1_cm
        elif bordo1 in ["inferiore", "basso", "fondo", "frontale", "bottom", "sotto"]:
            target_y = min_v + dist1_cm
        elif bordo1 in ["superiore", "alto", "sopra", "posteriore", "top"]:
            target_y = max_v - dist1_cm

        # Asse determinato da bordo 2
        if bordo2 in ["sinistra", "sinistro", "left"]:
            target_x = min_u + dist2_cm
        elif bordo2 in ["destra", "destro", "right"]:
            target_x = max_u - dist2_cm
        elif bordo2 in ["inferiore", "basso", "fondo", "frontale", "bottom", "sotto"]:
            target_y = min_v + dist2_cm
        elif bordo2 in ["superiore", "alto", "sopra", "posteriore", "top"]:
            target_y = max_v - dist2_cm

        # Crea punto di schizzo alle coordinate calcolate
        sp = sk.SketchPoints.Add(tg.CreatePoint2d(target_x, target_y))

        # Proietta gli spigoli di riferimento nello schizzo per le quote grafiche
        ref_edge1 = edges_map.get(bordo1)
        ref_edge2 = edges_map.get(bordo2)
        if ref_edge1:
            try:
                proj1 = sk.AddByProjectingEntity(ref_edge1)
                tp1 = tg.CreatePoint2d((min_u + target_x) / 2.0, target_y + 1.0)
                sk.DimensionConstraints.AddTwoPointDistance(proj1.StartSketchPoint, sp, 19203, tp1, False)
            except Exception:
                pass
        if ref_edge2:
            try:
                proj2 = sk.AddByProjectingEntity(ref_edge2)
                tp2 = tg.CreatePoint2d(target_x + 1.0, (min_v + target_y) / 2.0)
                sk.DimensionConstraints.AddTwoPointDistance(proj2.StartSketchPoint, sp, 19203, tp2, False)
            except Exception:
                pass

        try:
            sk.Solve()
        except Exception:
            pass

        coll = inv_app.TransientObjects.CreateObjectCollection()
        coll.Add(sp)
        placement_def = hole_features.CreateSketchPlacementDefinition(coll)
        return placement_def, f"Posizionato a {dist1_mm} mm da {bordo1} e {dist2_mm} mm da {bordo2} (X={target_x*10:.1f} mm, Y={target_y*10:.1f} mm)"

    # --- STRATEGIA 3: COORDINATE ASSOLUTE O CENTRO ---
    pos_x_mm = params.get("pos_x_mm", 0.0)
    pos_y_mm = params.get("pos_y_mm", 0.0)
    al_centro = params.get("al_centro", False) or (abs(pos_x_mm) < 1e-6 and abs(pos_y_mm) < 1e-6)

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
        try:
            proj_origin = sk.AddByProjectingEntity(cd.WorkPoints.Item(1))
            tp_x = tg.CreatePoint2d(pos_x_cm / 2.0, pos_y_cm + 1.0)
            sk.DimensionConstraints.AddTwoPointDistance(proj_origin, sp, 19203, tp_x, False)
            tp_y = tg.CreatePoint2d(pos_x_cm + 1.0, pos_y_cm / 2.0)
            sk.DimensionConstraints.AddTwoPointDistance(proj_origin, sp, 19203, tp_y, False)
        except Exception:
            pass
        msg = f"Posizionamento a coordinate X={pos_x_mm} mm, Y={pos_y_mm} mm"

    try:
        sk.Solve()
    except Exception:
        pass

    coll = inv_app.TransientObjects.CreateObjectCollection()
    coll.Add(sp)
    placement_def = hole_features.CreateSketchPlacementDefinition(coll)
    return placement_def, msg
