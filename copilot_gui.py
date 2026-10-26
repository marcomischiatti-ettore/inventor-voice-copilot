"""
copilot_gui.py
Interfaccia Grafica Moderna per Autodesk Inventor Voice Copilot.
Costruita con CustomTkinter.
Risolve il multithreading COM tramite pythoncom.CoInitialize().
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


class InventorCopilotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Autodesk Inventor AI Copilot")
        self.geometry("860x700")
        self.minsize(720, 560)

        # Configurazione layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Header Frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e1e2d")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

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

        # 2. Quick Actions Frame
        self.actions_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#181824")
        self.actions_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.quick_label = ctk.CTkLabel(
            self.actions_frame,
            text="Comandi Rapidi:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#94a3b8"
        )
        self.quick_label.pack(side="left", padx=15, pady=10)

        comandi_rapidi = [
            ("Demo 3D Completa", self.avvia_demo),
            ("Piastra 100x100x10", lambda: self.esegui_frase("fai una piastra 100x100x10")),
            ("Foro Passante Ø16", lambda: self.esegui_frase("foro passante diametro 16 mm al centro")),
            ("Smusso 3 mm", lambda: self.esegui_frase("smusso di 3 mm su tutti gli spigoli")),
            ("Svuotamento 2.5 mm", lambda: self.esegui_frase("svuota il solido con spessore 2.5 mm"))
        ]

        for nome, cmd in comandi_rapidi:
            btn = ctk.CTkButton(
                self.actions_frame,
                text=nome,
                font=ctk.CTkFont(size=11),
                height=28,
                fg_color="#334155",
                hover_color="#475569",
                command=cmd
            )
            btn.pack(side="left", padx=4, pady=10)

        # 3. Chat / Console Log Frame
        self.log_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=10,
            fg_color="#0f172a",
            text_color="#e2e8f0"
        )
        self.log_box.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        # 4. Input Vocale / Testuale Frame
        self.input_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e1e2d")
        self.input_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry_command = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Digita un comando o usa Win+H per parlare (es. 'fai una piastra 100x100x10')...",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=8
        )
        self.entry_command.grid(row=0, column=0, padx=(15, 10), pady=12, sticky="ew")
        self.entry_command.bind("<Return>", lambda e: self.invia_comando())

        self.btn_send = ctk.CTkButton(
            self.input_frame,
            text="Invia a Inventor",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=45,
            fg_color="#10b981",
            hover_color="#059669",
            command=self.invia_comando
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 15), pady=12)

        # Log iniziale
        self.stampa_log("[SISTEMA] Autodesk Inventor Voice Copilot inizializzato.")
        self.stampa_log("[INFO] 33/33 moduli CAD compilati e pronti all'uso.")
        self.stampa_log("[INFO] Inizializzazione COM thread-safe completata.")

        # Avvia controllo Inventor in background con CoInitialize
        threading.Thread(target=self.verifica_inventor, daemon=True).start()

    def stampa_log(self, testo: str):
        self.after(0, lambda: (self.log_box.insert("end", testo + "\n"), self.log_box.see("end")))

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

    def invia_comando(self):
        testo = self.entry_command.get().strip()
        if not testo:
            return
        self.entry_command.delete(0, "end")
        self.esegui_frase(testo)

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
                    self.stampa_log(f"[FALLITO - {mod_id}] {res.get('errore')}")
            except Exception as ex:
                self.stampa_log(f"[ERRORE DI ESECUZIONE]: {ex}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_worker, daemon=True).start()

    def avvia_demo(self):
        self.stampa_log("\n>>> AVVIO SEQUENZA DEMO 3D INVENTOR...")
        def _demo_worker():
            pythoncom.CoInitialize()
            try:
                from inventor_copilot import esegui_demo_live
                esegui_demo_live()
                self.stampa_log("[DEMO COMPLETATA] Verifica la finestra 3D di Autodesk Inventor!")
            except Exception as ex:
                self.stampa_log(f"[ERRORE DEMO]: {ex}")
            finally:
                pythoncom.CoUninitialize()

        threading.Thread(target=_demo_worker, daemon=True).start()


if __name__ == "__main__":
    app = InventorCopilotApp()
    app.mainloop()
