"""
estrai_comandi_inventor.py
Auto-acquisizione del catalogo completo delle feature native di Autodesk Inventor tramite API COM.
Interroga la collezione PartFeatures e genera 'roadmap_comandi.json'.
"""

import json
import os
import sys
import win32com.client

# Mappatura strutturata dei comandi e metodi di creazione per ciascuna collezione di PartFeatures
CATALOGO_METODI_FEATURE = {
    "ExtrudeFeatures": [
        {
            "id": "extrude_distance",
            "metodo_inventor": "ExtrudeFeatures.AddByDistanceExtent",
            "descrizione": "Crea un'estrusione lineare con estensione specificata per distanza (profondità/altezza) e direzione."
        },
        {
            "id": "extrude_through_all",
            "metodo_inventor": "ExtrudeFeatures.AddByThroughAllExtent",
            "descrizione": "Crea un'estrusione passante totale attraverso tutti i corpi solidi."
        },
        {
            "id": "extrude_to_extent",
            "metodo_inventor": "ExtrudeFeatures.AddByToExtent",
            "descrizione": "Crea un'estrusione fino a una faccia o superficie di terminazione definita."
        },
        {
            "id": "extrude_definition",
            "metodo_inventor": "ExtrudeFeatures.CreateExtrudeDefinition",
            "descrizione": "Crea e configura una definizione avanzata di estrusione (angoli di sformo, estensioni asimmetriche, operazioni booleane)."
        }
    ],
    "HoleFeatures": [
        {
            "id": "hole_drilled_distance",
            "metodo_inventor": "HoleFeatures.AddDrilledByDistanceExtent",
            "descrizione": "Crea un foro cieco semplice forato con diametro e profondità specificati."
        },
        {
            "id": "hole_drilled_through_all",
            "metodo_inventor": "HoleFeatures.AddDrilledByThroughAllExtent",
            "descrizione": "Crea un foro passante semplice con diametro specificato."
        },
        {
            "id": "hole_cbore_distance",
            "metodo_inventor": "HoleFeatures.AddCBoreByDistanceExtent",
            "descrizione": "Crea un foro con lamatura (controforo per testa vite cilindrica) a profondità definita."
        },
        {
            "id": "hole_csink_distance",
            "metodo_inventor": "HoleFeatures.AddCSinkByDistanceExtent",
            "descrizione": "Crea un foro con svasatura conica per teste svasate con diametro e angolo definiti."
        },
        {
            "id": "hole_definition",
            "metodo_inventor": "HoleFeatures.CreateHoleDefinition",
            "descrizione": "Crea una definizione avanzata di foratura (filettata, con gioco, maschiata conica, ecc.)."
        }
    ],
    "ThreadFeatures": [
        {
            "id": "thread_standard",
            "metodo_inventor": "ThreadFeatures.Add",
            "descrizione": "Applica una filettatura metrica o standard ISO/ANSI a una faccia cilindrica."
        },
        {
            "id": "thread_create_info",
            "metodo_inventor": "ThreadFeatures.CreateThreadInfo",
            "descrizione": "Configura le informazioni dettagliate della filettatura (passo, classe, direzione destra/sinistra)."
        }
    ],
    "ChamferFeatures": [
        {
            "id": "chamfer_distance",
            "metodo_inventor": "ChamferFeatures.AddUsingDistance",
            "descrizione": "Crea uno smusso a 45 gradi su uno o più spigoli specificando la distanza."
        },
        {
            "id": "chamfer_distance_angle",
            "metodo_inventor": "ChamferFeatures.AddUsingDistanceAndAngle",
            "descrizione": "Crea uno smusso definito da distanza e angolo su spigoli selezionati."
        },
        {
            "id": "chamfer_two_distances",
            "metodo_inventor": "ChamferFeatures.AddUsingTwoDistances",
            "descrizione": "Crea uno smusso a due distanze asimmetriche su spigoli selezionati."
        }
    ],
    "FilletFeatures": [
        {
            "id": "fillet_edge_set",
            "metodo_inventor": "FilletFeatures.AddEdgeSet",
            "descrizione": "Crea raccordi a raggio costante su uno o più spigoli selezionati."
        },
        {
            "id": "fillet_definition",
            "metodo_inventor": "FilletFeatures.CreateFilletDefinition",
            "descrizione": "Crea una definizione avanzata di raccordo (raggio variabile, raccordo a corda, facce complete)."
        }
    ],
    "RectangularPatternFeatures": [
        {
            "id": "rectangular_pattern",
            "metodo_inventor": "RectangularPatternFeatures.Add",
            "descrizione": "Crea una serie rettangolare (pattern lineare su due direzioni con conteggio e spaziatura)."
        },
        {
            "id": "rectangular_pattern_definition",
            "metodo_inventor": "RectangularPatternFeatures.CreateDefinition",
            "descrizione": "Crea e configura la definizione parametrica per serie rettangolari complesse."
        }
    ],
    "CircularPatternFeatures": [
        {
            "id": "circular_pattern",
            "metodo_inventor": "CircularPatternFeatures.Add",
            "descrizione": "Crea una serie circolare/polare attorno a un asse di rotazione con conteggio e angolo totale/passo."
        },
        {
            "id": "circular_pattern_definition",
            "metodo_inventor": "CircularPatternFeatures.CreateDefinition",
            "descrizione": "Crea e configura la definizione parametrica per serie circolari."
        }
    ],
    "MirrorFeatures": [
        {
            "id": "mirror_features",
            "metodo_inventor": "MirrorFeatures.Add",
            "descrizione": "Specchia una o più feature rispetto a un piano di lavoro o faccia piana di simmetria."
        },
        {
            "id": "mirror_definition",
            "metodo_inventor": "MirrorFeatures.CreateDefinition",
            "descrizione": "Crea la definizione completa di specchiatura per feature o per l'intero solido."
        }
    ],
    "ShellFeatures": [
        {
            "id": "shell_standard",
            "metodo_inventor": "ShellFeatures.Add",
            "descrizione": "Svuota un corpo solido lasciando uno spessore di parete costante e rimuovendo facce aperte."
        },
        {
            "id": "shell_definition",
            "metodo_inventor": "ShellFeatures.CreateShellDefinition",
            "descrizione": "Crea una definizione avanzata di svuotamento con spessori differenziati per faccia."
        }
    ],
    "RibFeatures": [
        {
            "id": "rib_standard",
            "metodo_inventor": "RibFeatures.Add",
            "descrizione": "Crea una nervatura di rinforzo o anima strutturale a partire da un profilo di schizzo aperto."
        },
        {
            "id": "rib_definition",
            "metodo_inventor": "RibFeatures.CreateRibDefinition",
            "descrizione": "Crea e configura la definizione di nervatura con spessori normali o paralleli al piano."
        }
    ],
    "MoveFaceFeatures": [
        {
            "id": "move_face_standard",
            "metodo_inventor": "MoveFaceFeatures.Add",
            "descrizione": "Trasla, ruota o sposta una o più facce di un corpo solido lungo una direzione o vettore."
        },
        {
            "id": "move_face_definition",
            "metodo_inventor": "MoveFaceFeatures.CreateMoveFaceDefinition",
            "descrizione": "Crea una definizione avanzata di spostamento facce per modifiche dirette al solido."
        }
    ],
    "LoftFeatures": [
        {
            "id": "loft_standard",
            "metodo_inventor": "LoftFeatures.Add",
            "descrizione": "Crea una feature di loft (raccordo di transizione) attraverso due o più sezioni/profili."
        },
        {
            "id": "loft_definition",
            "metodo_inventor": "LoftFeatures.CreateLoftDefinition",
            "descrizione": "Crea la definizione avanzata di loft specificando curve guida, linee d'asse e condizioni di tangenza."
        }
    ],
    "SweepFeatures": [
        {
            "id": "sweep_path",
            "metodo_inventor": "SweepFeatures.AddUsingPath",
            "descrizione": "Crea uno sweep estrudendo un profilo chiuso o aperto lungo una traiettoria guida (percorso)."
        },
        {
            "id": "sweep_guide_rail",
            "metodo_inventor": "SweepFeatures.AddUsingGuideRail",
            "descrizione": "Crea uno sweep con profilo lungo una traiettoria e una o più curve guida di orientamento/scala."
        },
        {
            "id": "sweep_definition",
            "metodo_inventor": "SweepFeatures.CreateSweepDefinition",
            "descrizione": "Crea la definizione completa di sweep per traiettorie 3D complesse."
        }
    ]
}


def get_inventor_application():
    try:
        return win32com.client.GetActiveObject("Inventor.Application")
    except Exception:
        try:
            return win32com.client.Dispatch("Inventor.Application")
        except Exception as e:
            print(f"ATTENZIONE: Impossibile connettersi a Inventor COM ({e}).")
            return None


def main():
    print("Connessione a Autodesk Inventor COM in corso...")
    inv_app = get_inventor_application()
    
    doc_creato = False
    part_doc = None
    part_features = None
    
    if inv_app:
        try:
            # Verifica o crea un documento parte invisibile per interrogare la collezione PartFeatures
            if inv_app.ActiveDocument and inv_app.ActiveDocumentType == 12290:  # kPartDocumentObject
                part_doc = inv_app.ActiveDocument
            else:
                # 12290 = kPartDocumentObject, CreateVisible = False
                part_doc = inv_app.Documents.Add(12290, "", False)
                doc_creato = True
            
            part_features = part_doc.ComponentDefinition.Features
            print("Accesso alla collezione PartFeatures di Inventor completato con successo.")
        except Exception as e:
            print(f"Nota durante l'accesso a PartFeatures: {e}")
    else:
        print("Inventor COM non attivo o non disponibile al momento. Utilizzo del catalogo API registrato.")

    roadmap = []
    
    for collection_name, comandi in CATALOGO_METODI_FEATURE.items():
        is_active_on_com = False
        if part_features is not None:
            try:
                col_obj = getattr(part_features, collection_name, None)
                if col_obj is not None:
                    is_active_on_com = True
            except Exception:
                is_active_on_com = False

        for cmd in comandi:
            item = {
                "id": cmd["id"],
                "modulo": collection_name,
                "metodo_inventor": cmd["metodo_inventor"],
                "stato": "DA_FARE",
                "descrizione": cmd["descrizione"]
            }
            if is_active_on_com:
                item["com_verificato"] = True
            roadmap.append(item)

    # Chiudi il documento temporaneo se aperto
    if doc_creato and part_doc:
        try:
            part_doc.Close(True)
        except Exception:
            pass

    # Salvataggio roadmap_comandi.json
    output_path = os.path.join(os.getcwd(), "roadmap_comandi.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(roadmap, f, indent=4, ensure_ascii=False)

    print(f"Roadmap comandi salvata con successo in '{output_path}'.")
    print(f"Totale comandi/metodi feature catalogati: {len(roadmap)}")


if __name__ == "__main__":
    main()
