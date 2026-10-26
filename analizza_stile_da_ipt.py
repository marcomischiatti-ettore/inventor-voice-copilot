"""
analizza_stile_da_ipt.py
Ispeziona a fondo i file .ipt presenti in 'miei_esempi/' interrogando Autodesk Inventor COM.
Estrae:
- GeometricConstraints e DimensionConstraints
- Metodo di vincolo rispetto all'origine (CenterPoint, WorkAxes, WorkPlanes)
- Status di vincolo (ConstraintStatusEnum: kFullyConstrainedConstraintStatus = 51713)
- Parametri di quota e convenzioni
"""

import glob
import os
import sys
import win32com.client

# Mappatura tipi vincoli geometrici Inventor
GEOM_CONSTRAINT_TYPES = {
    51457: "kCoincidentConstraintObject",
    51458: "kCollinearConstraintObject",
    51459: "kConcentricConstraintObject",
    51460: "kEqualConstraintObject",
    51461: "kHorizontalConstraintObject",
    51462: "kParallelConstraintObject",
    51463: "kPerpendicularConstraintObject",
    51464: "kSymmetricConstraintObject",
    51465: "kTangentConstraintObject",
    51466: "kVerticalConstraintObject",
    51467: "kFixConstraintObject",
    51468: "kSmoothConstraintObject",
    51469: "kMidpointConstraintObject",
    51470: "kOffsetConstraintObject"
}

# Mappatura tipi quote Inventor
DIM_CONSTRAINT_TYPES = {
    51969: "kTwoPointDistanceDimConstraintObject",
    51970: "kTwoLineAngleDimConstraintObject",
    51971: "kDiameterDimConstraintObject",
    51972: "kRadiusDimConstraintObject",
    51973: "kOffsetDimConstraintObject",
    51974: "kTangentDistanceDimConstraintObject",
    51975: "kThreePointAngleDimConstraintObject",
    51976: "kEllipseRadiusDimConstraintObject",
    51977: "kArcLengthDimConstraintObject"
}

CONSTRAINT_STATUS = {
    51713: "COMPLETAMENTE VINCOLATO (kFullyConstrainedConstraintStatus)",
    51714: "SOVRAVINCOLATO (kOverConstrainedConstraintStatus)",
    51715: "SOTTOVINCOLATO (kUnderConstrainedConstraintStatus)",
    51716: "SCONOSCIUTO (kUnknownConstraintStatus)"
}


def analizza_file_ipt(filepath, inv_app):
    filename = os.path.basename(filepath)
    print(f"\n=======================================================")
    print(f"ANALISI FILE: {filename}")
    print(f"=======================================================")

    doc = None
    try:
        # Assicurati che il percorso sia assoluto
        full_path = os.path.abspath(filepath)
        doc = inv_app.Documents.Open(full_path, False)
        cd = doc.ComponentDefinition
        
        report = {
            "filename": filename,
            "sketches": [],
            "features": [],
            "parametri": []
        }

        print(f"Documento aperto: {doc.DisplayName}")
        print(f"Numero di schizzi (Sketches): {cd.Sketches.Count}")
        print(f"Numero di corpi solidi: {cd.SurfaceBodies.Count}")
        print(f"Numero di WorkPlanes: {cd.WorkPlanes.Count}")

        # 1. Analisi Schizzi
        for idx in range(1, cd.Sketches.Count + 1):
            sk = cd.Sketches.Item(idx)
            sk_info = {
                "name": sk.Name,
                "piano_supporto": str(sk.PlanarEntity.Name if hasattr(sk.PlanarEntity, 'Name') else type(sk.PlanarEntity)),
                "constraint_status": CONSTRAINT_STATUS.get(sk.ConstraintStatus, f"Codice {sk.ConstraintStatus}"),
                "linee_count": sk.SketchLines.Count,
                "cerchi_count": sk.SketchCircles.Count,
                "archi_count": sk.SketchArcs.Count,
                "punti_count": sk.SketchPoints.Count,
                "vincoli_geometrici": [],
                "quote_dimensionali": []
            }

            print(f"\n--- Schizzo {idx}: '{sk.Name}' ---")
            print(f"Piano di supporto: {sk_info['piano_supporto']}")
            print(f"Stato vincoli: {sk_info['constraint_status']}")
            print(f"Entità: Linee={sk.SketchLines.Count}, Cerchi={sk.SketchCircles.Count}, Archi={sk.SketchArcs.Count}, Punti={sk.SketchPoints.Count}")

            # Vincoli Geometrici
            print(f"Vincoli geometrici totali: {sk.GeometricConstraints.Count}")
            for g_idx in range(1, sk.GeometricConstraints.Count + 1):
                try:
                    gc = sk.GeometricConstraints.Item(g_idx)
                    g_type_name = GEOM_CONSTRAINT_TYPES.get(gc.Type, f"Tipo_{gc.Type}")
                    sk_info["vincoli_geometrici"].append(g_type_name)
                except Exception as eg:
                    pass

            from collections import Counter
            c_geom = Counter(sk_info["vincoli_geometrici"])
            for g_type, count in c_geom.items():
                print(f"  * {g_type}: {count}")

            # Quote Dimensionali (DimensionConstraints)
            print(f"Quote dimensionali totali: {sk.DimensionConstraints.Count}")
            for d_idx in range(1, sk.DimensionConstraints.Count + 1):
                try:
                    dc = sk.DimensionConstraints.Item(d_idx)
                    d_type_name = DIM_CONSTRAINT_TYPES.get(dc.Type, f"Tipo_{dc.Type}")
                    param_name = dc.Parameter.Name if hasattr(dc, 'Parameter') and dc.Parameter else "N/A"
                    param_expr = dc.Parameter.Expression if hasattr(dc, 'Parameter') and dc.Parameter else "N/A"
                    param_val = dc.Parameter.ModelValue if hasattr(dc, 'Parameter') and dc.Parameter else "N/A"
                    dim_str = f"{d_type_name} -> {param_name} = {param_expr} ({param_val})"
                    sk_info["quote_dimensionali"].append(dim_str)
                    print(f"  * Quota {d_idx}: {dim_str}")
                except Exception as ed:
                    print(f"  * Quota {d_idx}: errore lettura ({ed})")

            # Verifica linee di costruzione
            construction_lines = 0
            centerlines = 0
            for l_idx in range(1, sk.SketchLines.Count + 1):
                line = sk.SketchLines.Item(l_idx)
                if line.Construction:
                    construction_lines += 1
                if hasattr(line, 'Centerline') and line.Centerline:
                    centerlines += 1
            print(f"Linee di costruzione: {construction_lines}, Assi mezzeria: {centerlines}")

            report["sketches"].append(sk_info)

        # 2. Analisi Features
        print(f"\nFeatures nel modello: {cd.Features.Count}")
        for f_idx in range(1, cd.Features.Count + 1):
            feat = cd.Features.Item(f_idx)
            print(f"  * Feature {f_idx}: {feat.Name} (Tipo: {feat.Type})")
            report["features"].append(f"{feat.Name} ({feat.Type})")

        return report

    except Exception as e:
        print(f"ERRORE durante l'analisi di {filename}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if doc:
            try:
                doc.Close(True)
            except Exception:
                pass


def main():
    print("Avvio ispezione file di esempio dell'utente...")
    files = glob.glob(os.path.join("miei_esempi", "*.ipt"))
    if not files:
        print("Nessun file .ipt trovato in 'miei_esempi/'.")
        return

    inv_app = None
    try:
        inv_app = win32com.client.GetActiveObject("Inventor.Application")
    except Exception:
        inv_app = win32com.client.Dispatch("Inventor.Application")

    tutti_report = []
    for f in sorted(files):
        rep = analizza_file_ipt(f, inv_app)
        if rep:
            tutti_report.append(rep)

    # Scrivi il resoconto completo
    out_file = "analisi_stile_utente.txt"
    with open(out_file, "w", encoding="utf-8") as f_out:
        for r in tutti_report:
            f_out.write(f"\n=====================================\nFILE: {r['filename']}\n")
            for sk in r["sketches"]:
                f_out.write(f"\nSchizzo: {sk['name']} (Piano: {sk['piano_supporto']})\n")
                f_out.write(f"Stato Vincoli: {sk['constraint_status']}\n")
                f_out.write(f"Vincoli Geometrici: {', '.join(sk['vincoli_geometrici'])}\n")
                f_out.write(f"Quote Dimensionali:\n")
                for q in sk["quote_dimensionali"]:
                    f_out.write(f"  - {q}\n")

    print(f"\nAnalisi completata! Risultati salvati in '{out_file}'.")


if __name__ == "__main__":
    main()
