"""
copilot_gui.py
Interfaccia Grafica Moderna per Autodesk Inventor Voice Copilot.
Costruita con CustomTkinter.
Include Navigazione a Schede (TabControl / CTkTabview):
1. Modellazione / Copilot 3D
2. Messa in Tavola (.idw / .dwg)
3. Dashboard Grafici & Statistiche
"""

import os
import sys
import threading
import time
import pythoncom
import customtkinter as ctk

# Impostazioni tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

try:
    from inventor_copilot import interpreta_ed_esegui, esegui_demo_live
    from comandi.inventor_utils import get_inventor_app, get_or_create_part_doc
except ImportError:
    from comandi.inventor_utils import get_inventor_app, get_or_create_part_doc

from ui.tabs.modeling_tab import ModelingTab
from ui.tabs.drawing_tab import DrawingTab
from ui.tabs.charts_tab import ChartsTab
from commands.drawing_commands import crea_tavola_da_modello_attivo


class InventorCopilotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Autodesk Inventor AI Copilot")
        self.geometry("940x760")
        self.minsize(800, 620)

        # Configurazione layout principale
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Frame (Sempre visibile e condiviso)
        self.header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e1e2d")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Autodesk Inventor Copilot 3D",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#38bdf8"
        )
        self.title_label.pack(side="left", padx=20, pady=15)

        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="Verifica Inventor...",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#374151",
            text_color="#9ca3af",
            corner_radius=8,
            padx=12,
            pady=6
        )
        self.status_badge.pack(side="right", padx=15, pady=15)

        self.btn_connect = ctk.CTkButton(
            self.header_frame,
            text="Avvia/Aggancia Inventor",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.connetti_inventor
        )
        self.btn_connect.pack(side="right", padx=10, pady=15)

        # 2. Tabview Principale (Navigazione a Schede)
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color="#13131f",
            segmented_button_fg_color="#1e1e2d",
            segmented_button_selected_color="#2563eb",
            segmented_button_selected_hover_color="#1d4ed8",
            segmented_button_unselected_color="#1e1e2d",
            segmented_button_unselected_hover_color="#334155"
        )
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="nsew")

        # Creazione delle 3 schede
        self.tab_modeling_ui = self.tabview.add("Modellazione 3D")
        self.tab_drawing_ui = self.tabview.add("Messa in Tavola")
        self.tab_charts_ui = self.tabview.add("Grafici & Statistiche")

        # Configurazione layout interno schede
        self.tab_modeling_ui.grid_columnconfigure(0, weight=1)
        self.tab_modeling_ui.grid_rowconfigure(0, weight=1)
        self.tab_drawing_ui.grid_columnconfigure(0, weight=1)
        self.tab_drawing_ui.grid_rowconfigure(0, weight=1)
        self.tab_charts_ui.grid_columnconfigure(0, weight=1)
        self.tab_charts_ui.grid_rowconfigure(0, weight=1)

        # Inizializzazione viste delle schede
        self.modeling_view = ModelingTab(
            self.tab_modeling_ui,
            execute_command_callback=self.esegui_frase,
            launch_demo_callback=self.avvia_demo
        )
        self.modeling_view.pack(fill="both", expand=True)

        self.drawing_view = DrawingTab(
            self.tab_drawing_ui,
            log_callback=self.stampa_log,
            execute_drawing_callback=self.esegui_creazione_tavola,
            populate_titleblock_callback=self.esegui_compilazione_cartiglio
        )
        self.drawing_view.pack(fill="both", expand=True)

        self.charts_view = ChartsTab(self.tab_charts_ui)
        self.charts_view.pack(fill="both", expand=True)

        # Log iniziale nella scheda modellazione
        self.stampa_log("[SISTEMA] Autodesk Inventor Voice Copilot inizializzato.")
        self.stampa_log("[INFO] Smart Placement Attivo: supporta quote da bordi/spigoli, SelectSet a video e direzioni semantiche.")
        self.stampa_log("[INFO] Scheda 'Messa in Tavola' pronta: generazione automatica tavole 2D (.idw) da parti e assiemi.")
        self.stampa_log("[INFO] Inizializzazione COM thread-safe completata.")

        # Avvia controllo Inventor in background
        threading.Thread(target=self.verifica_inventor, daemon=True).start()

    def stampa_log(self, testo: str):
        self.after(0, lambda: self.modeling_view.append_log(testo))

    def aggiorna_badge(self, testo: str, fg: str, text_col: str):
        self.after(0, lambda: self.status_badge.configure(text=testo, fg_color=fg, text_color=text_col))

    def verifica_inventor(self):
        pythoncom.CoInitialize()
        try:
            import win32com.client
            app = None
            try:
                app = win32com.client.GetActiveObject("Inventor.Application")
            except Exception:
                pass

            if app:
                try:
                    app.Visible = True
                except Exception:
                    pass
                self.aggiorna_badge("Inventor: Collegato", "#166534", "#86efac")
                self.stampa_log("[STATUS] Autodesk Inventor attivo e collegato.")
            else:
                self.aggiorna_badge("Inventor: Non Rilevato", "#991b1b", "#fca5a5")
                self.stampa_log("[STATUS] Inventor non ancora aperto. Clicca su 'Avvia/Aggancia Inventor'.")
        except Exception as e:
            self.aggiorna_badge("Errore COM", "#991b1b", "#fca5a5")
            self.stampa_log(f"[ERRORE COM] {e}")
        finally:
            pythoncom.CoUninitialize()

    def connetti_inventor(self):
        self.stampa_log("[AZIONE] Connessione o avvio di Autodesk Inventor...")
        def _task():
            pythoncom.CoInitialize()
            try:
                import win32com.client
                app = None
                try:
                    app = win32com.client.GetActiveObject("Inventor.Application")
                except Exception:
                    app = win32com.client.Dispatch("Inventor.Application")

                app.Visible = True
                doc = get_or_create_part_doc(app, visible=True)
                self.aggiorna_badge("Inventor: Pronto & Visibile", "#166534", "#86efac")
                self.stampa_log(f"[SUCCESSO] Inventor attivo! Finestra e documento {doc.DisplayName} pronti.")
            except Exception as e:
                self.stampa_log(f"[ERRORE] Impossibile avviare Inventor: {e}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_task, daemon=True).start()

    def esegui_frase(self, frase: str):
        self.stampa_log(f"\n>>> COMANDO UTENTE: \"{frase}\"")
        def _worker():
            pythoncom.CoInitialize()
            try:
                from inventor_copilot import interpreta_ed_esegui
                mod_id, res = interpreta_ed_esegui(frase, test_mode=False)
                if res.get("successo"):
                    self.stampa_log(f"[OK - {mod_id}] {res.get('dettagli')}")
                else:
                    self.stampa_log(f"[FALLITO - {mod_id}] Errore: {res.get('errore')}")
            except Exception as e:
                self.stampa_log(f"[ECCEZIONE] {e}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_worker, daemon=True).start()

    def esegui_creazione_tavola(self, formato: str, orientamento: str, cartiglio: str, bordo: str = "Bordo di default"):
        self.stampa_log(f"\n>>> AZIONE: Generazione nuova tavola 2D (Foglio: {formato}, Orientamento: {orientamento}, Cartiglio: {cartiglio}, Bordo: {bordo})...")
        def _worker():
            pythoncom.CoInitialize()
            try:
                res = crea_tavola_da_modello_attivo(
                    formato_foglio=formato,
                    orientamento=orientamento,
                    nome_cartiglio=cartiglio,
                    nome_bordo=bordo,
                    test_mode=False
                )
                if res.get("successo"):
                    self.stampa_log(f"[OK - Messa in Tavola]\n{res.get('dettagli')}")
                else:
                    self.stampa_log(f"[ERRORE - Messa in Tavola] {res.get('errore')}")
            except Exception as e:
                self.stampa_log(f"[ECCEZIONE Messa in Tavola] {e}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_worker, daemon=True).start()

    def esegui_compilazione_cartiglio(self):
        self.stampa_log("\n>>> AZIONE: Compilazione cartiglio tavola attiva da modello 3D...")
        def _worker():
            pythoncom.CoInitialize()
            try:
                from commands.drawing_commands import compila_cartiglio_disegno
                res = compila_cartiglio_disegno(test_mode=False)
                if res.get("successo"):
                    self.stampa_log(f"[OK - Cartiglio]\n{res.get('dettagli')}")
                else:
                    self.stampa_log(f"[ERRORE - Cartiglio] {res.get('errore')}")
            except Exception as e:
                self.stampa_log(f"[ECCEZIONE Cartiglio] {e}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_worker, daemon=True).start()

    def avvia_demo(self):
        self.stampa_log("\n>>> AVVIO DEMO 3D COMPLETA...")
        def _worker():
            pythoncom.CoInitialize()
            try:
                from inventor_copilot import esegui_demo_live
                esegui_demo_live()
                self.stampa_log("[OK] Demo 3D completata con successo!")
            except Exception as e:
                self.stampa_log(f"[ERRORE DEMO] {e}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_worker, daemon=True).start()


def avvia_gui():
    app = InventorCopilotApp()
    app.mainloop()


if __name__ == "__main__":
    avvia_gui()
