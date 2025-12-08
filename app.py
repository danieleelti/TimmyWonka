import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic
import aiversion
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import re

# --- 0. GESTIONE DATABASE (GOOGLE SHEETS) ---
SHEET_NAME = "TimmyWonka_DB"
# Nuova costante per il nome della scheda del catalogo
CATALOG_SHEET_TITLE = "CatalogoCompleto" 

def get_db_connection(worksheet_index=0):
    """Restituisce la connessione a una specifica scheda (index 0 è la prima)."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            # sheet.get_worksheet(0) per la prima scheda (Archivio Idee)
            # sheet.worksheet(CATALOG_SHEET_TITLE) per la scheda Catalogo
            return client.open(SHEET_NAME).get_worksheet(worksheet_index)
        return None
    except Exception as e:
        # Aggiungo debug per vedere se manca la scheda
        if "worksheet index out of range" in str(e) and worksheet_index > 0:
             print(f"DB Connection Error: Scheda con indice {worksheet_index} non trovata.")
        else:
             print(f"DB Connection Error: {e}")
        return None

def load_db_ideas():
    # Legge il foglio Archivio (indice 0)
    sheet = get_db_connection(worksheet_index=0)
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

def load_catalog_titles():
    """Carica solo Titoli e Temi dal Catalogo Completo."""
    try:
        # Legge il foglio CatalogoCompleto (indice 1, se il Catalogo è la seconda scheda)
        # ASSICURATI che 'CatalogoCompleto' sia la SECONDA scheda del tuo file Sheets (indice 1)
        sheet = get_db_connection(worksheet_index=1) 
        if sheet:
            # Recupera solo le colonne 'Titolo' e 'Tema' per minimizzare i token
            titles = sheet.col_values(1)[1:] if sheet.col_values(1) else []
            themes = sheet.col_values(2)[1:] if sheet.col_values(2) else []
            
            # Combina i dati in una lista di stringhe compatta per il prompt AI
            catalog_list = [f"Titolo: {t}, Tema: {th}" for t, th in zip(titles, themes) if t and th]
            return catalog_list
        return []
    except Exception as e:
        # Stampa l'errore per il debug interno
        print(f"Errore caricamento Catalogo: {e}")
        return []


def save_to_gsheet(title, theme, vibe, author, full_concept):
    # Legge il foglio Archivio (indice 0)
    sheet = get_db_connection(worksheet_index=0)
    if sheet:
        try:
            # La logica di controllo duplicati qui è molto base (solo sul titolo nella scheda di archivio)
            # La vera logica di controllo (vs Catalogo Completo) deve essere fatta con l'AI prima di chiamare questa funzione
            try:
                titles = sheet.col_values(1)
            except:
                titles = []
            
            if title in titles:
                return False 
            
            if not titles:
                sheet.append_row(["Titolo", "Tema", "Vibe", "Data", "Autore", "Concept"])

            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            row = [title, theme, vibe, date_str, author, full_concept]
            sheet.append_row(row)
            return True
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")
            return False
    return False

# ... (Il resto del codice rimane invariato tranne che per l'uso della nuova funzione) ...

# Modifica nella FASE 1: Ideazione
# ... (all'interno del blocco principale) ...

# FASE 1
st.header("Fase 1: Ideazione 💡")
activity_input = st.text_area("Tema Base", placeholder="Es. Robot Wars, La caccia al tesoro...", height=150)

if st.button("✨ Inventa 2 Idee", type="primary"):
    with st.spinner("Brainstorming..."):
        
        # 3. INTEGRAZIONE: Carica il catalogo e lo include nel prompt (SOLUZIONE PIÙ COMPLETA)
        catalog_list = load_catalog_titles()
        catalog_prompt = "\n".join(catalog_list)
        
        budget_str = "Libero" if (capex+opex+rrp)==0 else f"Fissi {capex}€, Var {opex}€, Vendita {rrp}€"
        
        prompt = f"""
        Genera 2 concept distinti per: {activity_input}. 
        Vibe: {vibes_input}. Budget: {budget_str}. 
        Logistica: {tech_level}, {phys_level}, {', '.join(locs)}.
        
        IMPORTANTE: NON generare idee che siano simili a quelle presenti nel Catalogo Completo sottostante.
        Catalogo Completo (Titolo e Tema):
        ---
        {catalog_prompt}
        ---
        """
        response = call_ai(provider, selected_model, api_key, prompt, json_mode=True)
        # ... (Il resto della FASE 1) ...

# ... (Il resto del codice fino alla fine) ...
