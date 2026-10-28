"""
commands/drawing_commands.py
Logica di automazione COM per Autodesk Inventor (DrawingDocument, Sheets, DrawingViews, TitleBlocks).
Supporta:
- Rilevamento e validazione documento 3D attivo (.ipt o .iam)
- Creazione nuovo disegno (.idw / .dwg)
- Configurazione formato foglio (A2, A3, A4, A5) e orientamento (Orizzontale, Verticale)
- Inserimento dinamico del cartiglio con fallback ed estrazione dai disegni aperti/template
- Inserimento vista base frontale centrata con rimozione linee nascoste
- Supporto simulazione (test_mode=True)
- Transazione atomica Inventor
"""

import os
from typing import Dict, Any, List, Optional
import pythoncom

# Enumeratori Autodesk Inventor Drawing
# Document Types
kPartDocumentObject = 12290
kAssemblyDocumentObject = 12291
kDrawingDocumentObject = 12292

# DrawingSheetSizeEnum
kA5DrawingSheetSize = 9993
kA4DrawingSheetSize = 9994
kA3DrawingSheetSize = 9995
kA2DrawingSheetSize = 9996
kCustomDrawingSheetSize = 9999

MAPPA_FORMATI_FOGLIO = {
    "A5": kA5DrawingSheetSize,
    "A4": kA4DrawingSheetSize,
    "A3": kA3DrawingSheetSize,
    "A2": kA2DrawingSheetSize,
}

# PageOrientationTypeEnum
kPortraitPageOrientation = 10241
kLandscapePageOrientation = 10242

MAPPA_ORIENTAMENTO = {
    "Orizzontale": kLandscapePageOrientation,
    "Verticale": kPortraitPageOrientation,
    "Landscape": kLandscapePageOrientation,
    "Portrait": kPortraitPageOrientation,
}

# ViewOrientationTypeEnum & DrawingViewStyleEnum
kFrontViewOrientation = 10754
kHiddenLineDrawingViewStyle = 10243


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


def get_available_title_blocks(inv_app=None) -> List[str]:
    """
    Recupera dinamicamente i nomi dei cartigli disponibili.
    Cerca prima in tutti i disegni attualmente aperti in Inventor.
    Se non trova disegni aperti, fornisce una lista standard con le definizioni tipiche ISO/UNI.
    """
    if inv_app is None:
        try:
            inv_app = get_inventor_app_safe()
        except Exception:
            inv_app = None

    cartigli_trovati = set()

    if inv_app is not None:
        try:
            # 1. Controlla in tutti i documenti aperti se c'è un disegno
            for i in range(1, inv_app.Documents.Count + 1):
                doc = inv_app.Documents.Item(i)
                if doc.DocumentType == kDrawingDocumentObject:
                    try:
                        for j in range(1, doc.TitleBlockDefinitions.Count + 1):
                            name = doc.TitleBlockDefinitions.Item(j).Name
                            if name:
                                cartigli_trovati.add(name)
                    except Exception:
                        pass
        except Exception:
            pass

    # Se abbiamo trovato cartigli nel disegno attivo o nei disegni aperti, restituiamoli
    lista = sorted(list(cartigli_trovati))
    
    # Includi sempre "Nessuno" e le opzioni standard se la lista è vuota
    if not lista:
        lista = ["Cartiglio ISO", "Cartiglio Standard", "Cartiglio Ridotto"]
    
    if "Nessuno" not in lista:
        lista.append("Nessuno")
        
    return lista


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
    
    Parametri:
    - formato_foglio: "A2", "A3", "A4", "A5" (default "A3")
    - orientamento: "Orizzontale" (Landscape) o "Verticale" (Portrait)
    - nome_cartiglio: Nome del cartiglio desiderato (oppure None per default, o "Nessuno")
    - scala: Scala della vista base (default 1.0 per 1:1, oppure calcolata automaticamente)
    - test_mode: Se True, simula l'operazione senza chiamare Inventor COM
    - template_path: Percorso opzionale al template .idw aziendale
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
            f"Cartiglio: '{nome_cartiglio or 'Default'}', Scala: {scala}"
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
        # Cerca tra i documenti aperti se ce n'è almeno una parte o assieme
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

    # 3. Transazione di configurazione foglio, cartiglio e vista base
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

        # 3.2 Gestione Cartiglio
        if nome_cartiglio:
            if nome_cartiglio.strip().lower() == "nessuno":
                if sheet.TitleBlock:
                    sheet.TitleBlock.Delete()
            else:
                # Controlla se la definizione esiste nel documento disegno
                target_def = None
                try:
                    for k in range(1, draw_doc.TitleBlockDefinitions.Count + 1):
                        tb_def = draw_doc.TitleBlockDefinitions.Item(k)
                        if tb_def.Name.strip().lower() == nome_cartiglio.strip().lower():
                            target_def = tb_def
                            break
                except Exception:
                    pass

                if target_def:
                    try:
                        if sheet.TitleBlock:
                            sheet.TitleBlock.Delete()
                        sheet.AddTitleBlock(target_def)
                    except Exception:
                        pass

        # 3.3 Inserimento Vista Base Principale (Frontale)
        # Calcolo punto centrale del foglio
        center_x = sheet.Width / 2.0
        center_y = sheet.Height / 2.0
        tg = inv_app.TransientGeometry
        placement_pt = tg.CreatePoint2d(center_x, center_y)

        # Inserimento vista
        drawing_views = sheet.DrawingViews
        base_view = drawing_views.AddBaseView(
            model_doc,
            placement_pt,
            scala,
            kFrontViewOrientation,
            kHiddenLineDrawingViewStyle
        )

        trans.End()

        try:
            draw_doc.Update2(True)
        except Exception:
            try:
                draw_doc.Update()
            except Exception:
                pass

        resoconto["successo"] = True
        resoconto["dettagli"] = (
            f"Tavola 2D creata con successo per '{model_doc.DisplayName}'!\n"
            f"- Foglio: {formato_foglio} ({orientamento})\n"
            f"- Cartiglio: {sheet.TitleBlock.Name if sheet.TitleBlock else 'Nessuno'}\n"
            f"- Vista Principale: {base_view.Name} (Scala {base_view.ScaleString})"
        )
        return resoconto

    except Exception as e:
        trans.Abort()
        resoconto["errore"] = f"Errore durante l'inserimento della vista o la formattazione: {e}"
        return resoconto
