"""
ui/dialogs/new_drawing_dialog.py
Finestra di dialogo modale (mascherina) per la configurazione del nuovo disegno 2D (.idw / .dwg):
- Selezione Formato Foglio: A2, A3, A4, A5 (Default: A3)
- Selezione Orientamento: Orizzontale (Landscape), Verticale (Portrait)
- Selezione Cartiglio: caricamento dinamico dai disegni aperti in Inventor
- Pulsanti di azione: 'Genera Tavola' e 'Annulla'
"""

import customtkinter as ctk
from typing import Callable, Optional, List
from commands.drawing_commands import get_available_title_blocks

class NewDrawingDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_confirm: Callable[[str, str, str], None]):
        super().__init__(parent)

        self.title("Messa in Tavola - Configurazione Disegno 2D")
        self.geometry("480x440")
        self.resizable(False, False)
        
        # Rendere la modale bloccante per il genitore
        self.transient(parent)
        self.grab_set()

        self.on_confirm = on_confirm

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#181824")
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Titolo
        self.lbl_title = ctk.CTkLabel(
            self.main_frame,
            text="Nuova Tavola 2D da Modello 3D",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_title.pack(pady=(15, 5))

        self.lbl_subtitle = ctk.CTkLabel(
            self.main_frame,
            text="Configura i parametri del foglio per il pezzo attivo in Inventor",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.lbl_subtitle.pack(pady=(0, 15))

        # 1. Selezione Formato Foglio
        self.lbl_formato = ctk.CTkLabel(
            self.main_frame,
            text="Formato Foglio:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9"
        )
        self.lbl_formato.pack(anchor="w", padx=25, pady=(5, 3))

        self.seg_formato = ctk.CTkSegmentedButton(
            self.main_frame,
            values=["A2", "A3", "A4", "A5"],
            selected_color="#2563eb",
            selected_hover_color="#1d4ed8",
            unselected_color="#334155",
            unselected_hover_color="#475569",
            height=32
        )
        self.seg_formato.set("A3")
        self.seg_formato.pack(fill="x", padx=25, pady=(0, 12))

        # 2. Selezione Orientamento
        self.lbl_orient = ctk.CTkLabel(
            self.main_frame,
            text="Orientamento:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9"
        )
        self.lbl_orient.pack(anchor="w", padx=25, pady=(5, 3))

        self.seg_orient = ctk.CTkSegmentedButton(
            self.main_frame,
            values=["Orizzontale", "Verticale"],
            selected_color="#2563eb",
            selected_hover_color="#1d4ed8",
            unselected_color="#334155",
            unselected_hover_color="#475569",
            height=32
        )
        self.seg_orient.set("Orizzontale")
        self.seg_orient.pack(fill="x", padx=25, pady=(0, 12))

        # 3. Selezione Cartiglio (Dinamico da Inventor)
        self.lbl_cartiglio = ctk.CTkLabel(
            self.main_frame,
            text="Cartiglio (Title Block):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9"
        )
        self.lbl_cartiglio.pack(anchor="w", padx=25, pady=(5, 3))

        # Recupera dinamicamente l'elenco cartigli da Inventor o fallback
        cartigli_disponibili = get_available_title_blocks()

        self.combo_cartiglio = ctk.CTkComboBox(
            self.main_frame,
            values=cartigli_disponibili,
            height=32,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=12),
            fg_color="#1e293b",
            button_color="#334155"
        )
        # Seleziona il primo cartiglio significativo o default
        if cartigli_disponibili:
            self.combo_cartiglio.set(cartigli_disponibili[0])
        self.combo_cartiglio.pack(fill="x", padx=25, pady=(0, 20))

        # 4. Pulsanti Azione
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=25, pady=(10, 15))
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_cancel = ctk.CTkButton(
            self.btn_frame,
            text="Annulla",
            font=ctk.CTkFont(size=13),
            height=36,
            fg_color="#475569",
            hover_color="#64748b",
            command=self.destroy
        )
        self.btn_cancel.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.btn_confirm = ctk.CTkButton(
            self.btn_frame,
            text="Genera Tavola",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._conferma
        )
        self.btn_confirm.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        # Focus
        self.lift()
        self.focus_force()

    def _conferma(self):
        formato = self.seg_formato.get()
        orient = self.seg_orient.get()
        cartiglio = self.combo_cartiglio.get()
        self.destroy()
        if self.on_confirm:
            self.on_confirm(formato, orient, cartiglio)
