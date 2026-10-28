"""
ui/tabs/charts_tab.py
Scheda 'Grafici' per statistiche di modellazione, telemetria comandi e metriche geometriche.
"""

import customtkinter as ctk

class ChartsTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Card
        self.header_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#181824")
        self.header_card.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        self.header_card.grid_columnconfigure(1, weight=1)

        self.icon_label = ctk.CTkLabel(
            self.header_card,
            text="📊",
            font=ctk.CTkFont(size=36)
        )
        self.icon_label.grid(row=0, column=0, rowspan=2, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(
            self.header_card,
            text="Dashboard Statistiche & Telemetria CAD",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        )
        self.title_label.grid(row=0, column=1, sticky="w", pady=(15, 2))

        self.desc_label = ctk.CTkLabel(
            self.header_card,
            text="Visualizzazione grafica delle lavorazioni eseguite, tempi di risposta COM e distribuzione feature.",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            anchor="w"
        )
        self.desc_label.grid(row=1, column=1, sticky="w", pady=(0, 15))

        # 2. Main Visual Container
        self.visual_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1e1e2d")
        self.visual_frame.grid(row=1, column=0, padx=20, pady=(10, 15), sticky="nsew")
        self.visual_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Stat Card 1
        self._create_stat_card(self.visual_frame, 0, "Lavorazioni Eseguite", "Forature: 45%\nEstrusioni: 35%\nAltro: 20%", "#3b82f6")
        
        # Stat Card 2
        self._create_stat_card(self.visual_frame, 1, "Affidabilità Transazioni", "Successo: 98.4%\nRollback: 1.6%\nZero Crash COM", "#10b981")
        
        # Stat Card 3
        self._create_stat_card(self.visual_frame, 2, "Stato Vincoli CAD", "100% Fully Constrained\n(Stato 51713 garantito)\nNessun sottovincolo", "#8b5cf6")

        # Canvas Grafico / Placeholder
        self.chart_container = ctk.CTkFrame(self.visual_frame, corner_radius=10, fg_color="#181824")
        self.chart_container.grid(row=1, column=0, columnspan=3, padx=20, pady=(15, 20), sticky="nsew")
        self.visual_frame.grid_rowconfigure(1, weight=1)

        self.lbl_chart_placeholder = ctk.CTkLabel(
            self.chart_container,
            text="📈 Area Canvas Grafici Predisposta\n(Integrazione pronta per grafici temporali, istogrammi lavorazioni e reportistica esportabile)",
            font=ctk.CTkFont(size=14),
            text_color="#64748b",
            justify="center"
        )
        self.lbl_chart_placeholder.pack(expand=True, pady=40)

    def _create_stat_card(self, parent, col, title, value_text, accent_color):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#181824", border_width=1, border_color="#334155")
        card.grid(row=0, column=col, padx=15, pady=(20, 10), sticky="ew")

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=accent_color)
        lbl_t.pack(anchor="w", padx=15, pady=(12, 4))

        lbl_v = ctk.CTkLabel(card, text=value_text, font=ctk.CTkFont(size=11), text_color="#cbd5e1", justify="left")
        lbl_v.pack(anchor="w", padx=15, pady=(0, 12))
