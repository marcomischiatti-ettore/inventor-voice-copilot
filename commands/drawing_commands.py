"""
commands/drawing_commands.py
Logica di automazione COM per Autodesk Inventor (DrawingDocument, Sheets, DrawingViews, TitleBlocks, Borders).
Risoluzione e allineamento con Inventor API 2021:
- Mapping rigoroso DrawingSheetSizeEnum:
    kA0DrawingSheetSize = 9993
    kA1DrawingSheetSize = 9994
    kA2DrawingSheetSize = 9995
    kA3DrawingSheetSize = 9996
    kA4DrawingSheetSize = 9997
    A5 gestito tramite kCustomDrawingSheetSize (9986) con dimensioni 21.0 x 14.8 cm.
- PageOrientationTypeEnum:
    kLandscapePageOrientation = 10242
    kPortraitPageOrientation = 10243
- ViewOrientationTypeEnum & Style:
    kFrontViewOrientation = 10764
    kHiddenLineRemovedDrawingViewStyle = 32258
- Gestione Intelligente Cartigli (TitleBlockDefinitions) e Bordi (BorderDefinitions):
    Se il nome selezionato appartiene a un Bordo ("No Contorno", "Bordo...") o a un Cartiglio,
    viene applicato correttamente nel rispettivo ramo (TitleBlock o Border).
    Se la definizione non è presente nel nuovo documento, viene importata via CopyTo() dal modello/disegno sorgente.
- Centratura e Fit della vista nel foglio (ThisApplication.ActiveView.Fit).
"""

import os
from typing import Dict, Any, List, Optional, Tuple
import pythoncom

# Document Types
kPartDocumentObject = 12290
kAssemblyDocumentObject = 12291
kDrawingDocumentObject = 12292

# DrawingSheetSizeEnum ufficiali Autodesk Inventor
kA0DrawingSheetSize = 9993
kA1DrawingSheetSize = 9994
kA2DrawingSheetSize = 9995
kA3DrawingSheetSize = 9996
kA4DrawingSheetSize = 9997
kCustomDrawingSheetSize = 9986

MAPPA_FORMATI_FOGLIO = {
    "A0": kA0DrawingSheetSize,
    "A1": kA1DrawingSheetSize,
    "A2": kA2DrawingSheetSize,
    "A3": kA3DrawingSheetSize,
    "A4": kA4DrawingSheetSize,
    "A5": kCustomDrawingSheetSize,
}

# PageOrientationTypeEnum
kLandscapePageOrientation = 10242
kPortraitPageOrientation = 10243

MAPPA_ORIENTAMENTO = {
    "Orizzontale": kLandscapePageOrientation,
    "Verticale": kPortraitPageOrientation,
    "Landscape": kLandscapePageOrientation,
    "Portrait": kPortraitPageOrientation,
}

# ViewOrientationTypeEnum & DrawingViewStyleEnum
kFrontViewOrientation = 10764
kTopViewOrientation = 10754
kHiddenLineRemovedDrawingViewStyle = 32258
kHiddenLineDrawingViewStyle = 32257


def get_inventor_app_safe():
    """Ottiene l'istanza attiva di Inventor con fallback su Dispatch."""
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


def get_available_drawing_resources(inv_app=None) -> Dict[str, List[str]]:
    """
    Rileva dinamicamente tutte le definizioni di Cartigli e Bordi presenti
    in tutti i disegni attualmente aperti in Inventor.
    """
    if inv_app is None:
        try:
            inv_app = get_inventor_app_safe()
        except Exception:
            inv_app = None

    cartigli = set()
    bordi = set()

    if inv_app is not None:
        try:
            for i in range(1, inv_app.Documents.Count + 1):
                doc = inv_app.Documents.Item(i)
                if doc.DocumentType == kDrawingDocumentObject:
                    try:
                        for j in range(1, doc.TitleBlockDefinitions.Count + 1):
                            name = doc.TitleBlockDefinitions.Item(j).Name
                            if name:
                                cartigli.add(name)
                    except Exception:
                        pass
                    try:
                        for j in range(1, doc.BorderDefinitions.Count + 1):
                            b_name = doc.BorderDefinitions.Item(j).Name
                            if b_name:
                                bordi.add(b_name)
                    except Exception:
                        pass
        except Exception:
            pass

    return {
        "cartigli": sorted(list(cartigli)),
        "bordi": sorted(list(bordi))
    }


def get_available_title_blocks(inv_app=None) -> List[str]:
    """
    Fornisce la lista combinata per il menu a tendina della UI:
    Include sia le definizioni di Cartiglio che eventuali definizioni di Bordo
    (es. 'No Contorno') trovate nei disegni aperti, più 'Nessuno'.
    """
    res = get_available_drawing_resources(inv_app)
    elenco = []

    # Cartigli trovati
    for c in res["cartigli"]:
        if c not in elenco:
            elenco.append(c)

    # Bordi trovati (es. "No Contorno", "Bordo standard")
    for b in res["bordi"]:
        if b not in elenco:
            elenco.append(b)

    if not elenco:
        elenco = ["Cartiglio ISO", "Cartiglio Standard", "No Contorno"]

    if "Nessuno" not in elenco:
        elenco.append("Nessuno")

    return elenco


def _trova_disegno_sorgente_risorsa(inv_app, nome_risorsa: str) -> Tuple[Optional[Any], str]:
    """Cerca in quale disegno aperto è contenuta la risorsa (se in TitleBlock o Border)."""
    nome_norm = nome_risorsa.strip().lower()
    for i in range(1, inv_app.Documents.Count + 1):
        doc = inv_app.Documents.Item(i)
        if doc.DocumentType == kDrawingDocumentObject:
            # Cerca tra i cartigli
            try:
                for j in range(1, doc.TitleBlockDefinitions.Count + 1):
                    tb = doc.TitleBlockDefinitions.Item(j)
                    if tb.Name.strip().lower() == nome_norm:
                        return tb, "titleblock"
            except Exception:
                pass
            # Cerca tra i bordi
            try:
                for j in range(1, doc.BorderDefinitions.Count + 1):
                    bd = doc.BorderDefinitions.Item(j)
                    if bd.Name.strip().lower() == nome_norm:
                        return bd, "border"
            except Exception:
                pass
    return None, "none"


def crea_tavola_da_modello_attivo(
    formato_foglio: str = "A3",
    orientamento: str = "Orizzontale",
    nome_cartiglio: Optional[str] = None,
    scala: float = 1.0,
    test_mode: bool = False,
    template_path: str = ""
) -> Dict[str, Any]:
    """
    Crea una nuova messa in tavola (.idw / .dwg) partendo dal modello 3D attivo (.ipt o .iam).
    Configura foglio, bordi, cartigli ed inserisce la vista frontale del solido centrata.
    """
    resoconto = {
        "successo": False,
        "formato_foglio": formato_foglio,
        "orientamento": orientamento,
        "nome_cartiglio": nome_cartiglio,
        "dettagli": "",
        "errore": None
    }

    if test_mode:
        resoconto["successo"] = True
        resoconto["dettagli"] = (
            f"Simulazione creazione tavola superata: Foglio {formato_foglio} {orientamento}, "
            f"Cartiglio/Bordo: '{nome_cartiglio or 'Default'}', Scala: {scala}"
        )
        return resoconto

    inv_app = get_inventor_app_safe()
    if not inv_app:
        resoconto["errore"] = "Impossibile connettersi ad Autodesk Inventor."
        return resoconto

    # 1. Rilevamento e validazione documento 3D attivo
    model_doc = None
    try:
        active_doc = inv_app.ActiveDocument
        if active_doc and active_doc.DocumentType in (kPartDocumentObject, kAssemblyDocumentObject):
            model_doc = active_doc
    except Exception as e:
        resoconto["errore"] = f"Errore durante l'accesso al documento attivo: {e}"
        return resoconto

    if model_doc is None:
        try:
            for i in range(1, inv_app.Documents.Count + 1):
                d = inv_app.Documents.Item(i)
                if d.DocumentType in (kPartDocumentObject, kAssemblyDocumentObject):
                    model_doc = d
                    break
        except Exception:
            pass

    if model_doc is None:
        resoconto["errore"] = (
            "Nessun modello 3D (.ipt o .iam) attivo in Inventor!\n"
            "Apri o crea prima una parte o un assieme prima di generare la messa in tavola."
        )
        return resoconto

    # 2. Creazione nuovo Documento Disegno (.idw)
    try:
        actual_template = template_path if (template_path and os.path.exists(template_path)) else ""
        draw_doc = inv_app.Documents.Add(kDrawingDocumentObject, actual_template, True)
    except Exception as e:
        resoconto["errore"] = f"Impossibile creare il nuovo documento disegno: {e}"
        return resoconto

    # 3. Configurazione Foglio, Cartiglio/Bordo e Vista Principale
    trans = inv_app.TransactionManager.StartTransaction(draw_doc, "Copilot_CreaTavolaDaModello")
    try:
        sheet = draw_doc.ActiveSheet
        
        # 3.1 Configurazione Dimensioni Foglio
        sheet_size_enum = MAPPA_FORMATI_FOGLIO.get(formato_foglio.upper(), kA3DrawingSheetSize)
        orientation_enum = MAPPA_ORIENTAMENTO.get(orientamento, kLandscapePageOrientation)
        
        try:
            sheet.Size = sheet_size_enum
        except Exception:
            pass
            
        try:
            sheet.Orientation = orientation_enum
        except Exception:
            pass

        # Per formato A5: usa dimensioni personalizzate esplicite in cm
        if formato_foglio.upper() == "A5":
            try:
                sheet.Size = kCustomDrawingSheetSize
                if orientation_enum == kLandscapePageOrientation:
                    sheet.Width = 21.0
                    sheet.Height = 14.8
                else:
                    sheet.Width = 14.8
                    sheet.Height = 21.0
            except Exception:
                pass

        # 3.2 Gestione Cartiglio & Bordo
        applicato_cartiglio = "Nessuno"
        applicato_bordo = "Predefinito"

        if nome_cartiglio:
            nome_c_clean = nome_cartiglio.strip()
            nome_c_lower = nome_c_clean.lower()

            if nome_c_lower == "nessuno":
                if sheet.TitleBlock:
                    try:
                        sheet.TitleBlock.Delete()
                    except Exception:
                        pass
                applicato_cartiglio = "Nessuno"
            else:
                # Ispezione risorsa: è un cartiglio o un bordo?
                source_def, def_kind = _trova_disegno_sorgente_risorsa(inv_app, nome_c_clean)

                if def_kind == "border" or "contorno" in nome_c_lower or "bordo" in nome_c_lower:
                    # È un Bordo (es. "No Contorno")!
                    # Se non presente nel nuovo documento disegno, copialo via CopyTo
                    target_b_def = None
                    try:
                        for b_idx in range(1, draw_doc.BorderDefinitions.Count + 1):
                            bd = draw_doc.BorderDefinitions.Item(b_idx)
                            if bd.Name.strip().lower() == nome_c_lower:
                                target_b_def = bd
                                break
                    except Exception:
                        pass

                    if target_b_def is None and source_def is not None:
                        try:
                            target_b_def = source_def.CopyTo(draw_doc, True)
                        except Exception:
                            pass

                    # Applica il bordo al foglio
                    if target_b_def:
                        try:
                            if sheet.Border:
                                sheet.Border.Delete()
                            sheet.AddBorder(target_b_def)
                            applicato_bordo = target_b_def.Name
                        except Exception:
                            pass
                    elif "no contorno" in nome_c_lower or "senza bordo" in nome_c_lower:
                        # Se è specificato "No Contorno" e non c'è una definizione grafica, rimuove il bordo
                        try:
                            if sheet.Border:
                                sheet.Border.Delete()
                            applicato_bordo = "Rimosso (Nessun Contorno)"
                        except Exception:
                            pass

                else:
                    # È un Cartiglio (TitleBlock)
                    target_tb_def = None
                    try:
                        for tb_idx in range(1, draw_doc.TitleBlockDefinitions.Count + 1):
                            tbd = draw_doc.TitleBlockDefinitions.Item(tb_idx)
                            if tbd.Name.strip().lower() == nome_c_lower:
                                target_tb_def = tbd
                                break
                    except Exception:
                        pass

                    if target_tb_def is None and source_def is not None:
                        try:
                            target_tb_def = source_def.CopyTo(draw_doc, True)
                        except Exception:
                            pass

                    if target_tb_def:
                        try:
                            if sheet.TitleBlock:
                                sheet.TitleBlock.Delete()
                            sheet.AddTitleBlock(target_tb_def)
                            applicato_cartiglio = target_tb_def.Name
                        except Exception:
                            pass

        # 3.3 Inserimento Vista Base Principale (Frontale)
        center_x = sheet.Width / 2.0
        center_y = sheet.Height / 2.0
        tg = inv_app.TransientGeometry
        placement_pt = tg.CreatePoint2d(center_x, center_y)

        # Inserimento vista base collegata al modello 3D attivo
        drawing_views = sheet.DrawingViews
        base_view = drawing_views.AddBaseView(
            model_doc,
            placement_pt,
            scala,
            kFrontViewOrientation,
            kHiddenLineRemovedDrawingViewStyle
        )

        trans.End()

        # Aggiornamento e Fit dello schermo
        try:
            draw_doc.Update2(True)
        except Exception:
            try:
                draw_doc.Update()
            except Exception:
                pass

        try:
            inv_app.ActiveView.Fit()
        except Exception:
            pass

        resoconto["successo"] = True
        resoconto["dettagli"] = (
            f"Tavola 2D generata con successo per '{model_doc.DisplayName}'!\n"
            f"- Foglio: {formato_foglio} ({orientamento}) [Larghezza: {sheet.Width:.1f} cm, Altezza: {sheet.Height:.1f} cm]\n"
            f"- Bordo: {applicato_bordo}\n"
            f"- Cartiglio: {sheet.TitleBlock.Name if sheet.TitleBlock else applicato_cartiglio}\n"
            f"- Vista Principale: {base_view.Name} (Scala {base_view.ScaleString}, Orientamento: Frontale)"
        )
        return resoconto

    except Exception as e:
        trans.Abort()
        resoconto["errore"] = f"Errore durante l'inserimento della vista o la formattazione: {e}"
        return resoconto
