"""
ui/tabs/modeling_tab.py
Scheda 'Modellazione / Copilot 3D' con controlli rapidi, console log e input comandi.
"""

import customtkinter as ctk
from typing import Callable

class ModelingTab(ctk.CTkFrame):
    def __init__(self, parent, execute_command_callback: Callable[[str], None], launch_demo_callback: Callable[[], None]):
        super().__init__(parent, fg_color="transparent")

        self.execute_command_callback = execute_command_callback
        self.launch_demo_callback = launch_demo_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Quick Actions Frame
        self.actions_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#181824")
        self.actions_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")

        self.quick_label = ctk.CTkLabel(
            self.actions_frame,
            text="Comandi Rapidi:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#94a3b8"
        )
        self.quick_label.pack(side="left", padx=15, pady=10)

        comandi_rapidi = [
            ("Demo 3D Completa", self.launch_demo_callback),
            ("Piastra 100x100x10", lambda: self.execute_command_callback("fai una piastra 100x100x10")),
            ("Foro da Bordi 20x30", lambda: self.execute_command_callback("foro passante diametro 10 a 20 mm da sinistra e 30 mm dal fondo")),
            ("Foro Passante Ø16", lambda: self.execute_command_callback("foro passante diametro 16 mm al centro")),
            ("Smusso 3 mm", lambda: self.execute_command_callback("smusso di 3 mm su tutti gli spigoli")),
            ("Svuota Parete 2.5", lambda: self.execute_command_callback("svuota il solido con spessore 2.5 mm"))
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

        # 2. Chat / Console Log Frame
        self.log_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=10,
            fg_color="#0f172a",
            text_color="#e2e8f0"
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # 3. Input Vocale / Testuale Frame
        self.input_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e1e2d")
        self.input_frame.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry_command = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Scrivi o usa Win+H (es. 'foro diametro 10 a 20 mm da sinistra e 30 mm da sotto', 'svuota faccia frontale')...",
            font=ctk.CTkFont(size=13),
            height=45,
            corner_radius=8
        )
        self.entry_command.grid(row=0, column=0, padx=(15, 10), pady=12, sticky="ew")
        self.entry_command.bind("<Return>", lambda e: self._invia_click())

        self.btn_send = ctk.CTkButton(
            self.input_frame,
            text="Invia a Inventor",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=45,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._invia_click
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 15), pady=12)

    def _invia_click(self):
        testo = self.entry_command.get().strip()
        if not testo:
            return
        self.entry_command.delete(0, "end")
        self.execute_command_callback(testo)

    def append_log(self, testo: str):
        self.log_box.insert("end", testo + "\n")
        self.log_box.see("end")
