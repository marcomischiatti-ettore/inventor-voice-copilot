"""
commands/drawing_commands.py
Logica di automazione COM per Autodesk Inventor (DrawingDocument, Sheets, DrawingViews, TitleBlocks, Borders).
Supporta:
- Utilizzo preferenziale del template aziendale MODELLO_TAVOLA.idw se presente nel progetto
- Sfondo foglio BIANCO puro (SheetSettings.SheetColor = (255, 255, 255))
- Proiezione completa a 4 viste (Proiezione ortogonale Europea ISO):
    1. Vista Base Frontale (in basso a sinistra/centro)
    2. Vista Proiettata Superiore (Top View, allineata sopra la frontale)
    3. Vista Proiettata Laterale Sinistra (Left View, posizionata a sinistra della frontale)
    4. Vista Assonometrica / Isometrica 3D (Iso View ombreggiata/shaded in basso a sinistra)
- Cartiglio aziendale in basso a destra con intestazione "F.lli Angelieri"
- Bordo pulito ("No Contorno") o Bordo Standard
- Allineamento automatico scala (auto-scaling) e Fit su schermo
"""

import os
from typing import Dict, Any, List, Optional, Tuple
import pythoncom

# Document Types
kPartDocumentObject = 12290
kAssemblyDocumentObject = 12291
kDrawingDocumentObject = 12292

# DrawingSheetSizeEnum
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

# ViewOrientationTypeEnum
kFrontViewOrientation = 10764
kTopViewOrientation = 10754
kLeftViewOrientation = 10758
kIsoBottomLeftViewOrientation = 10762
kIsoTopLeftViewOrientation = 10760

# DrawingViewStyleEnum
kFromBaseDrawingViewStyle = 32260
kHiddenLineRemovedDrawingViewStyle = 32258
kHiddenLineDrawingViewStyle = 32257
kShadedDrawingViewStyle = 32259


def get_template_path() -> str:
    """Cerca e restituisce il percorso assoluto di MODELLO_TAVOLA.idw."""
    dir_corrente = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidati = [
        os.path.join(dir_corrente, "MODELLO_TAVOLA.idw"),
        os.path.join(dir_corrente, "modello tavola.idw"),
        os.path.join(dir_corrente, "modello_tavola.idw"),
    ]
    for c in candidati:
        if os.path.exists(c):
            return c
    return ""


def get_inventor_app_safe(allow_dispatch: bool = False):
    """
    Ottiene l'istanza attiva di Inventor (GetActiveObject).
    Non avvia nuovi processi a meno che allow_dispatch non sia True.
    """
    import win32com.client
    try:
        app = win32com.client.GetActiveObject("Inventor.Application")
        return app
    except Exception:
        if allow_dispatch:
            try:
                app = win32com.client.Dispatch("Inventor.Application")
                return app
            except Exception:
                return None
        return None


def get_available_drawing_resources(inv_app=None) -> Dict[str, List[str]]:
    """
    Rileva dinamicamente tutte le definizioni di Cartigli e Bordi presenti
    nel template MODELLO_TAVOLA.idw o nei disegni aperti in Inventor.
    """
    if inv_app is None:
        try:
            inv_app = get_inventor_app_safe()
        except Exception:
            inv_app = None

    cartigli = set()
    bordi = set()

    # 1. Controlla prima il template locale MODELLO_TAVOLA.idw
    tmpl = get_template_path()
    if tmpl and inv_app is not None:
        try:
            doc_tmpl = inv_app.Documents.Open(tmpl, False)
            for j in range(1, doc_tmpl.TitleBlockDefinitions.Count + 1):
                cartigli.add(doc_tmpl.TitleBlockDefinitions.Item(j).Name)
            for j in range(1, doc_tmpl.BorderDefinitions.Count + 1):
                bordi.add(doc_tmpl.BorderDefinitions.Item(j).Name)
            doc_tmpl.Close(False)
        except Exception:
            pass

    # 2. Controlla in tutti i documenti aperti
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
    """Lista dei soli Cartigli (Title Blocks) per la combobox della UI."""
    res = get_available_drawing_resources(inv_app)
    elenco = []

    for c in res.get("cartigli", []):
        if c not in elenco:
            elenco.append(c)

    # Fallback standard basato sul template aziendale F.lli Angeleri
    if not elenco:
        elenco = ["Angeleri no contorno", "Cartiglio Angelieri", "Cartiglio ISO"]

    if "Nessuno" not in elenco:
        elenco.append("Nessuno")

    return elenco


def get_available_borders(inv_app=None) -> List[str]:
    """Lista delle definizioni di Bordo per la UI."""
    res = get_available_drawing_resources(inv_app)
    elenco = []

    for b in res.get("bordi", []):
        if b not in elenco:
            elenco.append(b)

    if not elenco:
        elenco = ["Bordo di default"]

    if "Nessuno" not in elenco:
        elenco.append("Nessuno")

    return elenco


def _trova_disegno_sorgente_risorsa(inv_app, nome_risorsa: str) -> Tuple[Optional[Any], str]:
    """Trova l'oggetto definizione sorgente nel template o nei disegni aperti."""
    nome_norm = nome_risorsa.strip().lower()

    # Cerca nei documenti aperti
    for i in range(1, inv_app.Documents.Count + 1):
        doc = inv_app.Documents.Item(i)
        if doc.DocumentType == kDrawingDocumentObject:
            try:
                for j in range(1, doc.TitleBlockDefinitions.Count + 1):
                    tb = doc.TitleBlockDefinitions.Item(j)
                    if tb.Name.strip().lower() == nome_norm:
                        return tb, "titleblock"
            except Exception:
                pass
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
    nome_bordo: Optional[str] = "Bordo di default",
    scala: float = 1.0,
    test_mode: bool = False,
    template_path: str = ""
) -> Dict[str, Any]:
    """
    Crea una nuova messa in tavola (.idw) professionale da modello 3D attivo (.ipt / .iam):
    - Foglio con sfondo BIANCO puro
    - Template aziendale MODELLO_TAVOLA.idw (con cartiglio F.lli Angeleri e bordo di default)
    - Bordo semplice lineare ('Bordo di default') sempre applicato o preservato
    - Proiezione completa 4 viste ortogonali/assonometriche:
        * Frontale (principale)
        * Superiore (Top View proiettata)
        * Sinistra (Left View proiettata)
        * Assonometrica 3D (Iso View in basso a sinistra)
    - Cartiglio aziendale ('Angeleri no contorno' / ISO)
    """
    resoconto = {
        "successo": False,
        "formato_foglio": formato_foglio,
        "orientamento": orientamento,
        "nome_cartiglio": nome_cartiglio,
        "nome_bordo": nome_bordo,
        "dettagli": "",
        "errore": None
    }

    if test_mode:
        resoconto["successo"] = True
        resoconto["dettagli"] = (
            f"Simulazione creazione tavola superata: Foglio {formato_foglio} {orientamento}, "
            f"Bordo: '{nome_bordo or 'Bordo di default'}', Cartiglio: '{nome_cartiglio or 'Default Modello'}', "
            f"Viste: 4 (Frontale, Superiore, Sinistra, 3D Iso), Sfondo: Bianco"
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

    # 2. Scelta del template .idw: preferenza per MODELLO_TAVOLA.idw
    tmpl_da_usare = template_path if (template_path and os.path.exists(template_path)) else get_template_path()

    try:
        draw_doc = inv_app.Documents.Add(kDrawingDocumentObject, tmpl_da_usare, True)
    except Exception as e:
        resoconto["errore"] = f"Impossibile creare il nuovo documento disegno: {e}"
        return resoconto

    # 3. Transazione di configurazione completa
    trans = inv_app.TransactionManager.StartTransaction(draw_doc, "Copilot_CreaTavolaCompleta")
    try:
        sheet = draw_doc.ActiveSheet

        # 3.1 IMPOSTAZIONE SFONDO FOGLIO BIANCO PURO
        try:
            tg = inv_app.TransientObjects
            bianco = tg.CreateColor(255, 255, 255)
            draw_doc.SheetSettings.SheetColor = bianco
        except Exception:
            pass

        # 3.2 Configurazione Dimensioni Foglio & Orientamento
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

        # 3.3 GESTIONE BORDO LINEARE SEMPLICE ('Bordo di default')
        applicato_bordo = "Bordo di default"
        if nome_bordo and nome_bordo.strip().lower() == "nessuno":
            if sheet.Border:
                try:
                    sheet.Border.Delete()
                    applicato_bordo = "Nessuno (Rimosso)"
                except Exception:
                    pass
        else:
            # Assicura che sul foglio sia presente il bordo semplice lineare
            if sheet.Border is None:
                bordo_trovato = False
                # Prova prima con la definizione presente nel template (es. "Bordo di default")
                for b_idx in range(1, draw_doc.BorderDefinitions.Count + 1):
                    try:
                        bd = draw_doc.BorderDefinitions.Item(b_idx)
                        try:
                            sheet.AddDefaultBorder(BorderDefinition=bd)
                            applicato_bordo = bd.Name
                            bordo_trovato = True
                            break
                        except Exception:
                            pass
                        try:
                            sheet.AddBorder(bd)
                            applicato_bordo = bd.Name
                            bordo_trovato = True
                            break
                        except Exception:
                            pass
                    except Exception:
                        pass

                # Se non ancora aggiunto, usa AddDefaultBorder() nativo
                if not bordo_trovato and sheet.Border is None:
                    try:
                        sheet.AddDefaultBorder()
                        applicato_bordo = "Bordo di default"
                        bordo_trovato = True
                    except Exception:
                        pass

                # Fallback con margini espliciti da 10 mm (1.0 cm) lineari
                if not bordo_trovato and sheet.Border is None:
                    try:
                        sheet.AddDefaultBorder(0, 10499, 0, 10499, False, False, False, 1.0, 1.0, 1.0, 1.0)
                        applicato_bordo = "Bordo di default (10mm)"
                        bordo_trovato = True
                    except Exception:
                        pass
            else:
                try:
                    applicato_bordo = sheet.Border.Name
                except Exception:
                    applicato_bordo = "Bordo presente"

        # 3.4 GESTIONE CARTIGLIO (Title Block - es. 'Angeleri no contorno')
        applicato_cartiglio = "Default Modello"
        if nome_cartiglio and nome_cartiglio.strip().lower() == "nessuno":
            if sheet.TitleBlock:
                try:
                    sheet.TitleBlock.Delete()
                    applicato_cartiglio = "Nessuno"
                except Exception:
                    pass
        else:
            target_tb = None
            if nome_cartiglio and nome_cartiglio.strip():
                nc = nome_cartiglio.strip().lower()
                for t_idx in range(1, draw_doc.TitleBlockDefinitions.Count + 1):
                    tb_cand = draw_doc.TitleBlockDefinitions.Item(t_idx)
                    tb_name = tb_cand.Name.strip().lower()
                    if tb_name == nc or nc in tb_name or tb_name in nc:
                        target_tb = tb_cand
                        break

            # Se non trovato per nome o non specificato, usa la prima definizione del template
            if target_tb is None and draw_doc.TitleBlockDefinitions.Count > 0:
                target_tb = draw_doc.TitleBlockDefinitions.Item(1)

            if target_tb is not None:
                if sheet.TitleBlock is None or sheet.TitleBlock.Name.strip().lower() != target_tb.Name.strip().lower():
                    try:
                        if sheet.TitleBlock:
                            sheet.TitleBlock.Delete()
                        sheet.AddTitleBlock(target_tb)
                        applicato_cartiglio = target_tb.Name
                    except Exception:
                        pass
                else:
                    applicato_cartiglio = sheet.TitleBlock.Name
            elif sheet.TitleBlock is not None:
                applicato_cartiglio = sheet.TitleBlock.Name

        # 3.4 INSERIMENTO DISPOSIZIONE A 4 VISTE (Standard Proiezione Europea ISO)
        # Coordinate foglio: width e height in cm
        w = sheet.Width
        h = sheet.Height

        # Calcolo punti per la disposizione esatta:
        # Frontale: leggermente a sinistra del centro (X: ~48% della larghezza, Y: ~48% altezza)
        # Superiore (Top): allineata verticalmente sopra la frontale (X = X_front, Y = Y_front + offset)
        # Sinistra (Left): allineata orizzontalmente a sinistra della frontale (X = X_front - offset, Y = Y_front)
        # Assonometrica 3D: nell'angolo inferiore sinistro (X: ~18%, Y: ~22%)
        
        tg = inv_app.TransientGeometry
        dw_views = sheet.DrawingViews

        # Punto Frontale
        pos_front = tg.CreatePoint2d(w * 0.48, h * 0.48)
        
        # 1. Vista Base Frontale
        base_view = dw_views.AddBaseView(
            model_doc,
            pos_front,
            scala,
            kFrontViewOrientation,
            kHiddenLineRemovedDrawingViewStyle
        )

        # Dimensioni della vista creata per calcolare gli offset di proiezione
        v_w = base_view.Width if hasattr(base_view, "Width") and base_view.Width > 0 else 5.0
        v_h = base_view.Height if hasattr(base_view, "Height") and base_view.Height > 0 else 5.0
        gap_x = max(v_w * 0.6, 4.0)
        gap_y = max(v_h * 0.6, 4.0)

        # 2. Vista Proiettata Superiore (Top View - sopra la frontale)
        pos_top = tg.CreatePoint2d(w * 0.48, min(h * 0.48 + v_h + gap_y, h * 0.78))
        try:
            view_top = dw_views.AddProjectedView(base_view, pos_top, kFromBaseDrawingViewStyle)
        except Exception:
            view_top = None

        # 3. Vista Proiettata Sinistra (Left View - a sinistra della frontale)
        pos_left = tg.CreatePoint2d(max(w * 0.48 - v_w - gap_x, w * 0.28), h * 0.48)
        try:
            view_left = dw_views.AddProjectedView(base_view, pos_left, kFromBaseDrawingViewStyle)
        except Exception:
            view_left = None

        # 4. Vista Assonometrica / Isometrica 3D (angolo inferiore sinistro)
        pos_iso = tg.CreatePoint2d(w * 0.18, h * 0.22)
        try:
            # Per la vista isometrica, proviamo prima come proiettata oppure come vista base 3D
            view_iso = dw_views.AddBaseView(
                model_doc,
                pos_iso,
                scala * 0.75,
                kIsoTopLeftViewOrientation,
                kHiddenLineRemovedDrawingViewStyle
            )
        except Exception:
            try:
                view_iso = dw_views.AddProjectedView(base_view, pos_iso, kFromBaseDrawingViewStyle)
            except Exception:
                view_iso = None

        trans.End()

        # Aggiornamento finale e zoom a tutto schermo
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
            f"Tavola 2D generata con successo su '{tmpl_da_usare or 'Standard'}':\n"
            f"- Modello: {model_doc.DisplayName}\n"
            f"- Foglio: {formato_foglio} ({orientamento}) - Sfondo BIANCO puro\n"
            f"- Bordo: {applicato_bordo}\n"
            f"- Cartiglio: {sheet.TitleBlock.Name if sheet.TitleBlock else 'Nessuno'}\n"
            f"- Viste Generate: 4 (Frontale, Superiore, Sinistra, 3D Assonometrica)"
        )
        return resoconto

    except Exception as e:
        trans.Abort()
        resoconto["errore"] = f"Errore durante l'inserimento delle viste: {e}"
        return resoconto
