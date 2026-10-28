"""
comandi/drawing_populate_titleblock.py
Modulo vocale e programmatico per compilare il cartiglio della tavola attiva in Autodesk Inventor.
"""
from typing import Dict, Any
from commands.drawing_commands import compila_cartiglio_disegno

def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    return compila_cartiglio_disegno(test_mode=test_mode)
