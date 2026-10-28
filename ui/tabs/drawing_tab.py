"""
ui/tabs/drawing_tab.py
Scheda 'Messa in Tavola' per la gestione di disegni 2D (.idw / .dwg) da parti e assiemi.
"""

import customtkinter as ctk
from typing import Callable
from ui.dialogs.new_drawing_dialog import NewDrawingDialog

class DrawingTab(ctk.CTkFrame):
    def __init__(self, parent, log_callback: Callable[[str], None], execute_drawing_callback: Callable[[str, str, str], None]):
        super().__init__(parent, fg_color="transparent")

        self.log_callback = log_callback
        self.execute_drawing_callback = execute_drawing_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Action Card Superiore
        self.card_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#181824")
        self.card_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        self.card_frame.grid_columnconfigure(1, weight=1)

        self.icon_label = ctk.CTkLabel(
            self.card_frame,
            text="📐",
            font=ctk.CTkFont(size=36)
        )
        self.icon_label.grid(row=0, column=0, rowspan=2, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(
            self.card_frame,
            text="Generazione Disegni 2D (.IDW / .DWG)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        )
        self.title_label.grid(row=0, column=1, sticky="w", pady=(15, 2))

        self.desc_label = ctk.CTkLabel(
            self.card_frame,
            text="Crea automaticamente la messa in tavola per il componente o assieme attivo in Inventor, "
                 "con calcolo scala, centratura vista e cartiglio personalizzato.",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            wraplength=520,
            justify="left",
            anchor="w"
        )
        self.desc_label.grid(row=1, column=1, sticky="w", pady=(0, 15))

        self.btn_crea_tavola = ctk.CTkButton(
            self.card_frame,
            text="Crea Tavola da Modello Attivo",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.apri_dialog_nuova_tavola
        )
        self.btn_crea_tavola.grid(row=0, column=2, rowspan=2, padx=25, pady=20)

        # 2. Informazioni & Dettagli Operativi
        self.info_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1e1e2d")
        self.info_frame.grid(row=1, column=0, padx=20, pady=(10, 15), sticky="nsew")
        self.info_frame.grid_columnconfigure(0, weight=1)

        self.lbl_info_title = ctk.CTkLabel(
            self.info_frame,
            text="Funzionalità & Specifiche Disegno:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f1f5f9"
        )
        self.lbl_info_title.pack(anchor="w", padx=20, pady=(15, 10))

        features = [
            ("📄 Supporto Formati Standard", "Generazione immediata fogli A2, A3 (default consigliato), A4 e A5."),
            ("🔄 Orientamento Automatico", "Opzione rapida Orizzontale (Landscape) o Verticale (Portrait)."),
            ("🏷️ Cartiglio Dinamico", "Rilevamento intelligente dei cartigli presenti nel modello/disegno aperto."),
            ("🎯 Vista Base Frontale", "Centratura automatica al centro geometrico del foglio con rimozione linee nascoste."),
            ("🔒 Transazione Sicura", "Creazione atomica: rollback automatico in caso di errore senza file orfani.")
        ]

        for tit, desc in features:
            item_box = ctk.CTkFrame(self.info_frame, fg_color="#181824", corner_radius=8)
            item_box.pack(fill="x", padx=20, pady=5)
            
            lbl_item_tit = ctk.CTkLabel(
                item_box,
                text=tit,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#38bdf8",
                anchor="w"
            )
            lbl_item_tit.pack(anchor="w", padx=12, pady=(6, 1))

            lbl_item_desc = ctk.CTkLabel(
                item_box,
                text=desc,
                font=ctk.CTkFont(size=11),
                text_color="#94a3b8",
                anchor="w"
            )
            lbl_item_desc.pack(anchor="w", padx=12, pady=(0, 6))

    def apri_dialog_nuova_tavola(self):
        NewDrawingDialog(self.winfo_toplevel(), on_confirm=self._on_drawing_confirmed)

    def _on_drawing_confirmed(self, formato: str, orientamento: str, cartiglio: str):
        if self.execute_drawing_callback:
            self.execute_drawing_callback(formato, orientamento, cartiglio)
