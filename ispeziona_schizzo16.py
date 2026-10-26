import win32com.client

app = win32com.client.Dispatch("Inventor.Application")
doc = app.Documents.Open(r"G:\Il mio Drive\Progetti AI\Inventor copilot\miei_esempi\Esempio-001.ipt", False)
cd = doc.ComponentDefinition
sk = cd.Sketches.Item("Schizzo16")

print("ConstraintStatus:", sk.ConstraintStatus)
print("Points in Sketch16:", sk.SketchPoints.Count)
for i in range(1, sk.SketchPoints.Count + 1):
    pt = sk.SketchPoints.Item(i)
    g = pt.Geometry
    print(f"Pt{i}: ({g.X:.2f}, {g.Y:.2f}) - HoleCenter={pt.HoleCenter}")

print("\n--- Geometric Constraints ---")
for i in range(1, sk.GeometricConstraints.Count + 1):
    c = sk.GeometricConstraints.Item(i)
    t = c.Type
    items = []
    for p in ['EntityOne', 'EntityTwo', 'LineOne', 'LineTwo', 'PointOne', 'PointTwo', 'Line', 'Point']:
        if hasattr(c, p):
            try:
                v = getattr(c, p)
                if v:
                    items.append(f"{p}={getattr(v, 'Type', type(v).__name__)}")
            except:
                pass
    print(f"GC {i} (Type {t}): {', '.join(items)}")

print("\n--- Dimension Constraints ---")
for i in range(1, sk.DimensionConstraints.Count + 1):
    d = sk.DimensionConstraints.Item(i)
    p = d.Parameter
    ent1 = getattr(d, 'EntityOne', None)
    ent2 = getattr(d, 'EntityTwo', None)
    line = getattr(d, 'Line', None)
    e1_t = getattr(ent1, 'Type', None) if ent1 else None
    e2_t = getattr(ent2, 'Type', None) if ent2 else None
    l_t = getattr(line, 'Type', None) if line else None
    print(f"Dim {i} (Type {d.Type}): {p.Name} = {p.Expression} | line={l_t}, e1={e1_t}, e2={e2_t}")

doc.Close(True)
