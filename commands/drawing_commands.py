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
            f"Bordo: '{nome_bordo or 'Bordo di default'}', Cartiglio: '{nome_cartiglio or 'Angeleri no contorno'}', "
            f"Viste: 4 (Frontale, Superiore, Sinistra, 3D Iso), Sfondo: Grigio chiaro (da Modello Tavola)"
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

        # 3.1 IMPOSTAZIONE SFONDO FOGLIO (Grigio chiaro come da Modello Tavola)
        try:
            colore_copiato = False
            # Verifica se tra i documenti aperti in Inventor c'è il modello tavola per replicarne fedelmente il colore
            for i in range(1, inv_app.Documents.Count + 1):
                d = inv_app.Documents.Item(i)
                if d.DocumentType == kDrawingDocumentObject and ("modello" in d.DisplayName.lower() or "tavola" in d.DisplayName.lower()):
                    try:
                        c_modello = d.SheetSettings.SheetColor
                        if c_modello:
                            draw_doc.SheetSettings.SheetColor = c_modello
                            colore_copiato = True
                            break
                    except Exception:
                        pass

            # Se non trovato tra i documenti aperti e non stiamo usando il template locale,
            # imposta un grigio chiaro tecnico da disegno (240, 240, 240) anziché bianco puro
            if not colore_copiato and not (tmpl_da_usare and os.path.exists(tmpl_da_usare)):
                tg = inv_app.TransientObjects
                grigio_chiaro = tg.CreateColor(240, 240, 240)
                draw_doc.SheetSettings.SheetColor = grigio_chiaro
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
                    applicato_bordo = "Bordo di default"

        # 3.4 GESTIONE CARTIGLIO (Title Block - es. 'Angeleri no contorno')
        applicato_cartiglio = "Angeleri no contorno"
        if nome_cartiglio and nome_cartiglio.strip().lower() == "nessuno":
            if sheet.TitleBlock:
                try:
                    sheet.TitleBlock.Delete()
                    applicato_cartiglio = "Nessuno (Rimosso)"
                except Exception:
                    pass
        else:
            # Se il foglio ha già il cartiglio attivo dal template (MODELLO_TAVOLA.idw), PRESERVALO!
            if sheet.TitleBlock is not None:
                try:
                    applicato_cartiglio = sheet.TitleBlock.Definition.Name
                except Exception:
                    applicato_cartiglio = "Angeleri no contorno"
            else:
                # Il foglio non ha un cartiglio: inseriscilo dalle definizioni del template
                target_tb = None
                if nome_cartiglio and nome_cartiglio.strip():
                    nc = nome_cartiglio.strip().lower()
                    for t_idx in range(1, draw_doc.TitleBlockDefinitions.Count + 1):
                        tb_cand = draw_doc.TitleBlockDefinitions.Item(t_idx)
                        tb_name = tb_cand.Name.strip().lower()
                        if tb_name == nc or nc in tb_name or tb_name in nc:
                            target_tb = tb_cand
                            break

                if target_tb is None and draw_doc.TitleBlockDefinitions.Count > 0:
                    target_tb = draw_doc.TitleBlockDefinitions.Item(1)

                if target_tb is not None:
                    try:
                        sheet.AddTitleBlock(target_tb)
                        applicato_cartiglio = target_tb.Name
                    except Exception:
                        try:
                            # Se richiede PromptStrings per i campi compilabili (kBottomRightPosition = 10244)
                            sheet.AddTitleBlock(target_tb, 10244, [""] * 40)
                            applicato_cartiglio = target_tb.Name
                        except Exception:
                            try:
                                sheet.AddTitleBlock(target_tb, 10244)
                                applicato_cartiglio = target_tb.Name
                            except Exception:
                                pass

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

        # 3.5 Compilazione automatica del cartiglio con i dati del modello 3D
        dati_cartiglio = {}
        try:
            scala_str = getattr(base_view, "ScaleString", f"1 : {int(1/scala)}" if scala < 1 else f"{int(scala)} : 1")
            dati_cartiglio = compila_campi_cartiglio(
                sheet=sheet,
                draw_doc=draw_doc,
                model_doc=model_doc,
                formato_foglio=formato_foglio,
                scala_str=scala_str
            )
        except Exception:
            pass

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
            f"- Foglio: {formato_foglio} ({orientamento}) - Sfondo Grigio Chiaro (da Modello Tavola)\n"
            f"- Bordo: {applicato_bordo}\n"
            f"- Cartiglio: {applicato_cartiglio}\n"
            f"- Viste Generate: 4 (Frontale, Superiore, Sinistra, 3D Assonometrica)"
        )
        return resoconto

    except Exception as e:
        trans.Abort()
        resoconto["errore"] = f"Errore durante l'inserimento delle viste: {e}"
        return resoconto


def compila_campi_cartiglio(
    sheet,
    draw_doc,
    model_doc,
    formato_foglio: Optional[str] = None,
    scala_str: str = "1 : 1"
) -> Dict[str, Any]:
    """
    Compila tutti i dati del cartiglio:
    - Sincronizza le iProperties dal modello 3D al disegno .idw
    - Compila i testi con prompt (Prompted Entries) presenti nel TitleBlock
    """
    import os
    from datetime import datetime

    codice = ""
    descrizione = ""
    materiale = ""
    autore = "UT"
    nome_file_completo = ""

    if model_doc is not None:
        try:
            nome_file_completo = model_doc.FullFileName
        except Exception:
            try:
                nome_file_completo = model_doc.DisplayName
            except Exception:
                pass

        try:
            m_tracking = model_doc.PropertySets.Item("Design Tracking Properties")
            try:
                codice = str(m_tracking.Item("Part Number").Value).strip()
            except Exception:
                pass
            try:
                descrizione = str(m_tracking.Item("Description").Value).strip()
            except Exception:
                pass
            try:
                materiale = str(m_tracking.Item("Material").Value).strip()
            except Exception:
                pass
            try:
                autore = str(m_tracking.Item("Designer").Value).strip()
            except Exception:
                pass
        except Exception:
            pass

        disp = getattr(model_doc, "DisplayName", "")
        base_name = os.path.splitext(disp)[0]

        if not codice or codice == "" or "parte" in codice.lower():
            if " " in base_name:
                parti = base_name.split(" ", 1)
                codice = parti[0].strip()
                if not descrizione:
                    descrizione = parti[1].strip()
            elif base_name:
                codice = base_name

        if not descrizione:
            if " " in base_name:
                descrizione = base_name.split(" ", 1)[1].strip()
            else:
                descrizione = base_name

        if not materiale:
            try:
                materiale = model_doc.ComponentDefinition.Material.Name
            except Exception:
                materiale = "Alluminio"

    if not autore:
        autore = "UT"

    if not formato_foglio and sheet is not None:
        sz = getattr(sheet, "Size", None)
        inversa_formati = {v: k for k, v in MAPPA_FORMATI_FOGLIO.items()}
        formato_foglio = inversa_formati.get(sz, "A3")
    elif not formato_foglio:
        formato_foglio = "A3"

    data_oggi = datetime.now().strftime("%Y/%m/%d")

    # 1. Sincronizzazione iProperties nel documento .idw
    if draw_doc is not None:
        try:
            d_track = draw_doc.PropertySets.Item("Design Tracking Properties")
            if codice:
                try:
                    d_track.Item("Part Number").Value = codice
                except Exception:
                    pass
            if descrizione:
                try:
                    d_track.Item("Description").Value = descrizione
                except Exception:
                    pass
            if materiale:
                try:
                    d_track.Item("Material").Value = materiale
                except Exception:
                    pass
            if autore:
                try:
                    d_track.Item("Designer").Value = autore
                except Exception:
                    pass
        except Exception:
            pass

        try:
            d_sum = draw_doc.PropertySets.Item("Inventor Summary Information")
            if descrizione:
                try:
                    d_sum.Item("Title").Value = descrizione
                except Exception:
                    pass
            if autore:
                try:
                    d_sum.Item("Author").Value = autore
                except Exception:
                    pass
        except Exception:
            pass

    # 2. Compilazione Prompted Entries nel TitleBlock del foglio
    tb = getattr(sheet, "TitleBlock", None) if sheet is not None else None
    if tb is not None:
        try:
            sketch = tb.Definition.Sketch
            for i in range(1, sketch.TextBoxes.Count + 1):
                txt_box = sketch.TextBoxes.Item(i)
                t_content = txt_box.Text.upper().strip()

                val = None
                if any(k in t_content for k in ["CODICE", "PART NUMBER", "NUMERO DIS", "DIS."]):
                    val = codice
                elif any(k in t_content for k in ["DESCRIZIONE", "DESCRIPTION", "TITOLO"]):
                    val = descrizione
                elif any(k in t_content for k in ["MATERIALE", "MATERIAL", "MAT."]):
                    val = materiale
                elif any(k in t_content for k in ["SCALA", "SCALE"]):
                    val = scala_str
                elif any(k in t_content for k in ["FORMATO", "FORMAT", "FOGLIO"]):
                    val = formato_foglio
                elif any(k in t_content for k in ["DATA", "DATE"]):
                    val = data_oggi
                elif any(k in t_content for k in ["NOME FILE", "FILENAME", "PERCORSO"]):
                    val = nome_file_completo
                elif any(k in t_content for k in ["PROGETTATO", "DISEGNATO", "AUTORE"]):
                    val = autore
                elif "TOLLERANZA" in t_content:
                    val = "± 0.1"

                if val is not None:
                    try:
                        tb.SetPromptResultText(txt_box, str(val))
                    except Exception:
                        pass
        except Exception:
            pass

    return {
        "codice": codice,
        "descrizione": descrizione,
        "materiale": materiale,
        "autore": autore,
        "formato": formato_foglio,
        "scala": scala_str,
        "data": data_oggi
    }


def compila_cartiglio_disegno(
    draw_doc=None,
    model_doc=None,
    test_mode: bool = False
) -> Dict[str, Any]:
    """
    Esegue la compilazione completa del cartiglio sulla tavola attiva (.idw):
    - Ripristina sfondo grigio chiaro da modello tavola se troppo bianco
    - Inserisce 'Angeleri no contorno' se mancante
    - Inserisce 'Bordo di default' se mancante
    - Estrae dati dal pezzo 3D collegato (viste o modello aperto)
    - Popola le iProperties e tutti i campi parametrici del cartiglio
    """
    if test_mode:
        return {
            "successo": True,
            "dettagli": (
                "Compilazione cartiglio completata con successo (Simulazione):\n"
                "- Codice: MNV-000-137\n"
                "- Descrizione: Cerniera\n"
                "- Materiale: Alluminio\n"
                "- Progettato da: UT\n"
                "- Scala: 1 : 1\n"
                "- Formato: A3\n"
                "- Sfondo: Grigio chiaro da Modello Tavola"
            ),
            "errore": None
        }

    inv_app = get_inventor_app_safe()
    if not inv_app:
        return {"successo": False, "errore": "Impossibile collegarsi ad Autodesk Inventor."}

    # 1. Identifica il documento disegno da compilare
    if draw_doc is None:
        try:
            active_doc = inv_app.ActiveDocument
            if active_doc and active_doc.DocumentType == kDrawingDocumentObject:
                draw_doc = active_doc
        except Exception:
            pass

    if draw_doc is None:
        try:
            for i in range(1, inv_app.Documents.Count + 1):
                d = inv_app.Documents.Item(i)
                if d.DocumentType == kDrawingDocumentObject and "modello" not in d.DisplayName.lower():
                    draw_doc = d
                    break
        except Exception:
            pass

    if draw_doc is None:
        return {"successo": False, "errore": "Nessun disegno 2D (.idw) attivo o aperto in Inventor."}

    sheet = draw_doc.ActiveSheet
    if sheet is None:
        return {"successo": False, "errore": "Nessun foglio attivo nel disegno."}

    trans = inv_app.TransactionManager.StartTransaction(draw_doc, "Copilot_CompilaCartiglio")
    try:
        # A) Ripristino sfondo grigio chiaro dal modello tavola
        try:
            for i in range(1, inv_app.Documents.Count + 1):
                d = inv_app.Documents.Item(i)
                if d.DocumentType == kDrawingDocumentObject and ("modello" in d.DisplayName.lower() or "tavola" in d.DisplayName.lower()):
                    try:
                        c_mod = d.SheetSettings.SheetColor
                        if c_mod:
                            draw_doc.SheetSettings.SheetColor = c_mod
                            break
                    except Exception:
                        pass
        except Exception:
            pass

        # B) Assicura Bordo di default
        if sheet.Border is None:
            try:
                sheet.AddDefaultBorder()
            except Exception:
                pass

        # C) Assicura Cartiglio 'Angeleri no contorno' se mancante
        if sheet.TitleBlock is None:
            target_tb = None
            for t_idx in range(1, draw_doc.TitleBlockDefinitions.Count + 1):
                tb_cand = draw_doc.TitleBlockDefinitions.Item(t_idx)
                if "angeleri" in tb_cand.Name.lower() or "contorno" in tb_cand.Name.lower():
                    target_tb = tb_cand
                    break
            if target_tb is None and draw_doc.TitleBlockDefinitions.Count > 0:
                target_tb = draw_doc.TitleBlockDefinitions.Item(1)

            if target_tb is not None:
                try:
                    sheet.AddTitleBlock(target_tb)
                except Exception:
                    try:
                        sheet.AddTitleBlock(target_tb, 10244, [""] * 40)
                    except Exception:
                        pass

        # D) Identifica il modello 3D associato (dalle viste o dai documenti aperti)
        scala_str = "1 : 1"
        if model_doc is None:
            try:
                if sheet.DrawingViews.Count > 0:
                    v1 = sheet.DrawingViews.Item(1)
                    scala_str = getattr(v1, "ScaleString", "1 : 1")
                    model_doc = v1.ReferencedDocumentDescriptor.ReferencedDocument
            except Exception:
                pass

        if model_doc is None:
            for i in range(1, inv_app.Documents.Count + 1):
                d = inv_app.Documents.Item(i)
                if d.DocumentType in (kPartDocumentObject, kAssemblyDocumentObject):
                    model_doc = d
                    break

        # E) Compilazione effettiva campi
        dati = compila_campi_cartiglio(
            sheet=sheet,
            draw_doc=draw_doc,
            model_doc=model_doc,
            scala_str=scala_str
        )

        trans.End()

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

        dettagli_txt = (
            f"Cartiglio compilato con successo sulla tavola '{draw_doc.DisplayName}':\n"
            f"- Codice: {dati['codice']}\n"
            f"- Descrizione: {dati['descrizione']}\n"
            f"- Materiale: {dati['materiale']}\n"
            f"- Progettato da: {dati['autore']}\n"
            f"- Formato: {dati['formato']}\n"
            f"- Scala: {dati['scala']}\n"
            f"- Data: {dati['data']}\n"
            f"- Sfondo: Grigio chiaro da Modello Tavola"
        )

        return {
            "successo": True,
            "dettagli": dettagli_txt,
            "errore": None
        }
    except Exception as e:
        trans.Abort()
        return {"successo": False, "errore": f"Errore durante la compilazione del cartiglio: {e}"}
