"""
comandi/drawing_create_from_active.py
Modulo vocale e programmatico per la Messa in Tavola da modello attivo in Autodesk Inventor.
"""
from typing import Dict, Any
import re
from commands.drawing_commands import crea_tavola_da_modello_attivo, get_available_title_blocks

def analizza_frase_vocale(frase: str) -> Dict[str, Any]:
    f = frase.lower().strip()
    
    # Formato foglio
    formato = "A3"
    m_f = re.search(r'\b(a[2345])\b', f)
    if m_f:
        formato = m_f.group(1).upper()
        
    # Orientamento
    orientamento = "Orizzontale"
    if "vertical" in f or "portrait" in f:
        orientamento = "Verticale"

    # Bordo
    nome_bordo = "Bordo di default"
    if "senza bordo" in f or "no bordo" in f:
        nome_bordo = "Nessuno"
        
    return {
        "formato_foglio": formato,
        "orientamento": orientamento,
        "nome_cartiglio": None,
        "nome_bordo": nome_bordo,
        "frase_originale": frase
    }

def esegui_comando(frase_vocale: str, test_mode: bool = False, part_doc=None) -> Dict[str, Any]:
    params = analizza_frase_vocale(frase_vocale)
    res = crea_tavola_da_modello_attivo(
        formato_foglio=params["formato_foglio"],
        orientamento=params["orientamento"],
        nome_cartiglio=params["nome_cartiglio"],
        nome_bordo=params.get("nome_bordo", "Bordo di default"),
        test_mode=test_mode
    )
    return res
