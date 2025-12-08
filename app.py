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

def get_db_connection():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet
        return None
    except Exception as e:
        st.error(f"❌ Errore DB: {e}")
        return None

def load_db_ideas():
    sheet = get_db_connection()
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

def save_to_gsheet(title, theme, vibe, author, full_concept):
    sheet = get_db_connection()
    if sheet:
        try:
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

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Timmy Wonka R&D",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; color: #6C3483; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .concept-card { border: 1px solid #ddd; padding: 20px; border-radius: 10px; background-color: #f8f9fa; margin-bottom: 20px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE SICUREZZA ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    try:
        secret = st.secrets["login_password"]
        if st.session_state.password_input == secret:
            st.session_state.authenticated = True
            del st.session_state.password_input
        else:
            st.error("🚫 Password Errata.")
    except:
        st.error("⚠️ Configurazione mancante.")

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Timmy Wonka R&D")
        st.text_input("Password", type="password", key="password_input", on_change=check_password)
        st.button("Entra 🔓", on_click=check_password)
    st.stop()

# ==============================================================================
# LOGICA AI (JSON MODE)
# ==============================================================================

SYSTEM_PROMPT = """
SEI TIMMY WONKA, Direttore R&D.
Il tuo compito è generare format di team building.
IMPORTANTE: Non usare mai acronimi tecnici (Capex/Opex) nelle risposte.

FORMATO OUTPUT RICHIESTO:
Devi rispondere SEMPRE E SOLO con un array JSON valido. 
Esempio:
[
  {"titolo": "Titolo Idea 1", "descrizione": "Dettagli completi..."},
  {"titolo": "Titolo Idea 2", "descrizione": "Dettagli completi..."}
]
Non aggiungere testo prima o dopo il JSON.
"""

def clean_json_text(text):
    """Pulisce la risposta dall'AI per estrarre solo il JSON."""
    text = text.strip()
    # Rimuove i backticks di markdown se presenti (```json ... ```)
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text)
        text = re.sub(r"```$", "", text)
    return text.strip()

def call_ai(provider, model_id, api_key, prompt):
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    try:
        text_response = ""
        if provider == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_id)
            response = model.generate_content(full_prompt)
            text_response = response.text
        elif provider == "ChatGPT":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            text_response = response.choices[0].message.content
        elif provider == "Claude (Anthropic)":
            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model=model_id, max_tokens=4000, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": prompt}]
            )
            text_response = message.content[0].text
        elif provider == "Groq":
            client = OpenAI(base_url="[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            text_response = response.choices[0].message.content
        elif provider == "Grok (xAI)":
            client = OpenAI(base_url="[https://api.x.ai/v1](https://api.x.ai/v1)", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            text_response = response.choices[0].message.content
        
        # Parsing JSON
        try:
            cleaned_text = clean_json_text(text_response)
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            # Se fallisce, ritorna errore gestito
            return [{"titolo": "Errore Formato", "descrizione": f"L'AI non ha risposto in JSON valido.\nRaw: {text_response}"}]
            
    except Exception as e:
        return [{"titolo": "Errore API", "descrizione": f"Errore tecnico: {str(e)}"}]

# ==============================================================================
# INTERFACCIA
# ==============================================================================

# --- SETUP ---
with st.expander("🧠 Configurazione Cervello AI", expanded=True):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: provider = st.selectbox("Provider", ["Google Gemini", "ChatGPT", "Claude (Anthropic)", "Groq", "Grok (xAI)"])
    with c2:
        key_map = {"Google Gemini": "GOOGLE_API_KEY", "ChatGPT": "OPENAI_API_KEY", "Claude (Anthropic)": "ANTHROPIC_API_KEY", "Groq": "GROQ_API_KEY", "Grok (xAI)": "XAI_API_KEY"}
        api_key = st.secrets.get(key_map[provider], st.text_input("API Key", type="password"))
    with c3:
        if api_key:
            if provider == "Google Gemini": models = aiversion.get_gemini_models(api_key)
            elif provider == "ChatGPT": models = aiversion.get_openai_models(api_key)
            elif provider == "Claude (Anthropic)": models = aiversion.get_anthropic_models(api_key)
            elif provider == "Groq": models = aiversion.get_openai_models(api_key, base_url="[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)")
            elif provider == "Grok (xAI)": models = aiversion.get_openai_models(api_key, base_url="[https://api.x.ai/v1](https://api.x.ai/v1)")
            else: models = []
        else: models = []
        
        selected_model = st.selectbox("Versione", models) if models and "Errore" not in models[0] else st.text_input("Versione Manuale")

st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🆕 Nuovo Format")
    st.subheader("1. Vibe & Keywords 🎨")
    vibes_input = st.text_area("Stile", height=100)
    st.divider()
    st.subheader("2. Logistica 📦")
    tech_level = st.select_slider("Tech", ["Low", "Hybrid", "High"])
    phys_level = st.select_slider("Fisicità", ["Sedentario", "Leggero", "Attivo"])
    locs = [l for l in ["Indoor", "Outdoor", "Dinner Game", "Ibrido", "Remoto"] if st.checkbox(l, value=(l=="Indoor"))]
    st.divider()
    st.subheader("3. Budget 💰")
    capex = st.number_input("Costi Fissi (€)", 0)
    opex = st.number_input("Costi Variabili/pax (€)", 0)
    rrp = st.number_input("Prezzo Vendita/pax (€)", 0)

# --- STATO ---
if "concepts_list" not in st.session_state: st.session_state.concepts_list = []
if "selected_concept" not in st.session_state: st.session_state.selected_concept = ""
if "assets" not in st.session_state: st.session_state.assets = ""

# --- MAIN ---
st.title("🦁 Timmy Wonka R&D")

# ARCHIVIO
with st.expander("📂 Archivio Idee (Database)", expanded=False):
    if st.button("🔄 Aggiorna DB"): st.rerun()
    saved = load_db_ideas()
    titles = [i['Titolo'] for i in saved if isinstance(i, dict) and 'Titolo' in i]
    sel_saved = st.selectbox("Carica idea salvata:", ["-- Scegli --"] + titles)
    if sel_saved != "-- Scegli --":
        data = next(i for i in saved if i['Titolo'] == sel_saved)
        if st.button("🔽 Carica in Fase 2"):
            st.session_state.selected_concept = sel_saved
            # Prepariamo un contesto fittizio per la fase 2
            st.session_state.assets = "" # Reset asset precedenti
            st.success(f"Caricato: {sel_saved}. Scorri giù.")

# FASE 1
st.header("Fase 1: Ideazione 💡")
activity_input = st.text_input("Tema Base", placeholder="Es. Robot Wars...")

# LOGICA BOTTONI
col_main_btn, _ = st.columns([1, 4])
if col_main_btn.button("✨ Inventa 3 Idee", type="primary"):
    with st.spinner("Brainstorming..."):
        budget_str = "Libero" if (capex+opex+rrp)==0 else f"Fissi {capex}€, Var {opex}€, Vendita {rrp}€"
        prompt = f"""
        Genera 3 concept distinti per: {activity_input}. 
        Vibe: {vibes_input}. Budget: {budget_str}. 
        Logistica: {tech_level}, {phys_level}, {', '.join(locs)}.
        Rispondi solo con JSON: [{{ "titolo": "...", "descrizione": "..." }}]
        """
        response = call_ai(provider, selected_model, api_key, prompt)
        if isinstance(response, list):
            st.session_state.concepts_list = response
        else:
            st.error("Errore nel formato AI")

# VISUALIZZAZIONE IDEE (Iterazione con pulsanti)
if st.session_state.concepts_list:
    st.divider()
    st.caption("Ecco le idee sfornate. Usa i pulsanti per gestirle.")
    
    # Loop attraverso la lista delle idee salvate in session state
    # Usiamo enumerate per avere un indice unico per le chiavi dei bottoni
    for idx, concept in enumerate(st.session_state.concepts_list):
        with st.container(border=True):
            st.subheader(f"{idx+1}. {concept.get('titolo', 'Senza Titolo')}")
            st.markdown(concept.get('descrizione', ''))
            
            c1, c2, c3 = st.columns([1, 1, 1])
            
            # 1. APPROFONDISCI
            if c1.button("🚀 Approfondisci", key=f"app_{idx}"):
                st.session_state.selected_concept = concept['titolo']
                st.session_state.assets = "" # Reset fase successiva
                st.success(f"Selezionato: {concept['titolo']}")
            
            # 2. SALVA
            if c2.button("💾 Salva per dopo", key=f"save_{idx}"):
                res = save_to_gsheet(concept['titolo'], activity_input, vibes_input, f"{provider}", str(concept))
                if res: st.toast(f"✅ Salvato: {concept['titolo']}")
                else: st.toast("⚠️ Già presente nel DB")

            # 3. RIGENERA (SOLO QUESTA IDEA)
            if c3.button("🔄 Rigenera (Boccia)", key=f"regen_{idx}"):
                with st.spinner(f"Rimpiazzo l'idea {idx+1}..."):
                    # Prompt specifico per sostituire solo questa
                    p_regen = f"""
                    L'utente ha scartato l'idea "{concept['titolo']}". 
                    Genera 1 NUOVO concept alternativo per il tema {activity_input}.
                    Stessi vincoli. Rispondi SOLO JSON: [{{ "titolo": "...", "descrizione": "..." }}]
                    """
                    new_concept = call_ai(provider, selected_model, api_key, p_regen)
                    if isinstance(new_concept, list) and len(new_concept) > 0:
                        st.session_state.concepts_list[idx] = new_concept[0]
                        st.rerun() # Ricarica la pagina per mostrare la nuova idea

# FASE 2
if st.session_state.selected_concept:
    st.divider()
    st.header(f"Fase 2: Deep Dive su '{st.session_state.selected_concept}' 🛠️")
    
    if st.button(f"Genera Scheda Tecnica con {provider}"):
        with st.spinner("Elaborazione tecnica..."):
            # Qui il prompt può essere testuale normale, non serve JSON
            prompt = f"""
            Scheda tecnica dettagliata per il format: "{st.session_state.selected_concept}".
            Tema: {activity_input}. Vibe: {vibes_input}.
            Output richiesto in Markdown ben formattato.
            NO Acronimi.
            """
            st.session_state.assets = call_ai(provider, selected_model, api_key, prompt) # Qui potrebbe tornare stringa o json, gestiamo nel call_ai

# Visualizzazione Asset (Fase 2 Output)
if st.session_state.assets:
    # Se call_ai ritorna JSON per errore (perché il system prompt è fissato su JSON), 
    # lo convertiamo in stringa leggibile o forziamo la visualizzazione
    content_to_show = st.session_state.assets
    if isinstance(content_to_show, list) or isinstance(content_to_show, dict):
        content_to_show = str(content_to_show) # Fallback grezzo se torna JSON
        # Nota: Idealmente dovremmo fare una funzione call_ai_text separata, 
        # ma per semplicità ora mostriamo quello che arriva.
    
    with st.expander("📝 VEDI SCHEDA TECNICA", expanded=True):
        st.markdown(content_to_show)

# FASE 3
if st.session_state.assets:
    st.header("Fase 3: Sales Pitch 💼")
    if st.button("Genera Slide"):
        with st.spinner("Writing pitch..."):
            p_pitch = f"Sales pitch per '{st.session_state.selected_concept}'. Target HR. Prezzo {rrp}."
            # Per il pitch vogliamo testo libero, non JSON.
            # Trucco: aggiungiamo un override al prompt per ignorare il JSON constraint
            p_pitch += "\nIGNORA ISTRUZIONI JSON. Rispondi in testo semplice Markdown per le slide."
            
            pitch_res = call_ai(provider, selected_model, api_key, p_pitch)
            # Gestione fallback se torna lista
            if isinstance(pitch_res, list): pitch_res = str(pitch_res)
            
            st.markdown(pitch_res)
            st.download_button("Scarica Pitch", pitch_res, "pitch.txt")

st.markdown("---")
st.caption("Timmy Wonka v2.5 (Interactive Cards)" - Powered by Teambuilding.it")
