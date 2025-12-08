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
        print(f"DB Connection Error: {e}")
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

if "login_password" not in st.secrets:
    st.error("⚠️ Configurazione Errata: Manca la chiave 'login_password' nel file secrets.toml.")
    st.info("Aggiungi: login_password = \"LaTuaPassword\" nei secrets.")
    st.stop()

def check_password():
    if 'password_input' not in st.session_state:
        return
        
    password_typed = st.session_state.password_input

    if password_typed == st.secrets["login_password"]:
        st.session_state.authenticated = True
        del st.session_state.password_input
    else:
        st.error("🚫 Password Errata.")

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Timmy Wonka R&D")
        st.text_input("Password", type="password", key="password_input") 
        st.button("Entra 🔓", on_click=check_password)
    st.stop()

# ==============================================================================
# LOGICA AI
# ==============================================================================

SYSTEM_PROMPT = """
SEI TIMMY WONKA, Direttore R&D di Teambuilding.it.
Obiettivo: Format di team building reali, scalabili e ad alto margine.
IMPORTANTE: Non usare mai acronimi tecnici (Capex/Opex) nelle risposte. Usa "Costi Fissi", "Costi Variabili".
"""

def clean_json_text(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text)
        text = re.sub(r"```$", "", text)
    return text.strip()

def call_ai(provider, model_id, api_key, prompt, json_mode=False):
    if json_mode:
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}\n\nRISPONDI SOLO CON UN ARRAY JSON VALIDO: [{{...}}, {{...}}]. Niente testo extra."
    else:
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
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}]
            )
            text_response = response.choices[0].message.content
        elif provider == "Claude (Anthropic)":
            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model=model_id, max_tokens=4000, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": full_prompt}]
            )
            text_response = message.content[0].text
        elif provider == "Groq":
            client = OpenAI(base_url="[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}]
            )
            text_response = response.choices[0].message.content
        elif provider == "Grok (xAI)":
            client = OpenAI(base_url="[https://api.x.ai/v1](https://api.x.ai/v1)", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full_prompt}]
            )
            text_response = response.choices[0].message.content
        
        if json_mode:
            try:
                cleaned_text = clean_json_text(text_response)
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                return [{"titolo": "Errore Formato", "descrizione": f"L'AI non ha risposto in JSON valido.\nRaw: {text_response}"}]
        else:
            return text_response
            
    except Exception as e:
        if json_mode: return [{"titolo": "Errore API", "descrizione": f"Errore tecnico: {str(e)}"}]
        else: return f"❌ Errore API: {str(e)}"

# ==============================================================================
# INTERFACCIA
# ==============================================================================

# --- SETUP ---
with st.expander("🧠 Configurazione Cervello AI", expanded=True):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: 
        provider = st.selectbox("Provider", ["Google Gemini", "ChatGPT", "Claude (Anthropic)", "Groq", "Grok (xAI)"])
    
    with c2:
        key_map = {"Google Gemini": "GOOGLE_API_KEY", "ChatGPT": "OPENAI_API_KEY", "Claude (Anthropic)": "ANTHROPIC_API_KEY", "Groq": "GROQ_API_KEY", "Grok (xAI)": "XAI_API_KEY"}
        secret_key_name = key_map[provider]
        
        if secret_key_name in st.secrets:
            api_key = st.secrets[secret_key_name]
        else:
            api_key = st.text_input("Inserisci API Key", type="password")

    with c3:
        models = []
        if api_key:
            try:
                if provider == "Google Gemini": models = aiversion.get_gemini_models(api_key)
                elif provider == "ChatGPT": models = aiversion.get_openai_models(api_key)
                elif provider == "Claude (Anthropic)": models = aiversion.get_anthropic_models(api_key)
                elif provider == "Groq": models = aiversion.get_openai_models(api_key, base_url="[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)")
                elif provider == "Grok (xAI)": models = aiversion.get_openai_models(api_key, base_url="[https://api.x.ai/v1](https://api.x.ai/v1)")
            except:
                models = []
        
        # LOGICA PER DEFAULT MODEL
        default_index = 0
        if models and "Errore" not in models[0]:
            if provider == "Google Gemini":
                default_model_name = "gemini-3-pro-preview"
                try:
                    default_index = models.index(default_model_name)
                except ValueError:
                    pass 
            
            selected_model = st.selectbox("Versione", models, index=default_index)
        else:
            selected_model = st.text_input("Versione Manuale (es. gemini-1.5-pro)")

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
    if not saved:
        st.info("Nessuna idea salvata o Database non connesso.")
    else:
        titles = [i['Titolo'] for i in saved if isinstance(i, dict) and 'Titolo' in i]
        sel_saved = st.selectbox("Carica idea salvata:", ["-- Scegli --"] + titles)
        if sel_saved != "-- Scegli --":
            if st.button("🔽 Carica in Fase 2"):
                st.session_state.selected_concept = sel_saved
                st.session_state.assets = ""
                st.success(f"Caricato: {sel_saved}. Scorri giù.")

# FASE 1
st.header("Fase 1: Ideazione 💡")
# CAMPO PRINCIPALE A TEXT_AREA (5+ righe)
activity_input = st.text_area("Tema Base", placeholder="Es. Robot Wars, La caccia al tesoro...", height=150)

if st.button("✨ Inventa 3 Idee", type="primary"):
    with st.spinner("Brainstorming..."):
        budget_str = "Libero" if (capex+opex+rrp)==0 else f"Fissi {capex}€, Var {opex}€, Vendita {rrp}€"
        prompt = f"""
        Genera 3 concept distinti per: {activity_input}. 
        Vibe: {vibes_input}. Budget: {budget_str}. 
        Logistica: {tech_level}, {phys_level}, {', '.join(locs)}.
        """
        response = call_ai(provider, selected_model, api_key, prompt, json_mode=True)
        if isinstance(response, list):
            st.session_state.concepts_list = response
        else:
            st.error("Errore formato AI: " + str(response))

# VISUALIZZAZIONE CARD
if st.session_state.concepts_list:
    st.divider()
    st.caption("Usa i pulsanti per gestire le idee:")
    
    for idx, concept in enumerate(st.session_state.concepts_list):
        with st.container(border=True):
            st.subheader(f"{idx+1}. {concept.get('titolo', 'Senza Titolo')}")
            st.markdown(concept.get('descrizione', ''))
            
            c1, c2, c3 = st.columns([1, 1, 1])
            
            if c1.button("🚀 Approfondisci", key=f"app_{idx}"):
                st.session_state.selected_concept = concept['titolo']
                st.session_state.assets = ""
                st.success(f"Selezionato: {concept['titolo']}")
            
            if c2.button("💾 Salva per dopo", key=f"save_{idx}"):
                res = save_to_gsheet(concept['titolo'], activity_input, vibes_input, f"{provider}", str(concept))
                if res: st.toast(f"✅ Salvato: {concept['titolo']}")
                else: st.toast("⚠️ Già nel DB")

            if c3.button("🔄 Rigenera (Boccia)", key=f"regen_{idx}"):
                with st.spinner(f"Rimpiazzo l'idea {idx+1}..."):
                    p_regen = f"""
                    L'utente ha scartato l'idea "{concept['titolo']}". 
                    Genera 1 NUOVO concept alternativo per il tema {activity_input}.
                    Stessi vincoli.
                    """
                    new_concept = call_ai(provider, selected_model, api_key, p_regen, json_mode=True)
                    if isinstance(new_concept, list) and len(new_concept) > 0:
                        st.session_state.concepts_list[idx] = new_concept[0]
                        st.rerun()

# FASE 2
if st.session_state.selected_concept:
    st.divider()
    st.header(f"Fase 2: Deep Dive su '{st.session_state.selected_concept}' 🛠️")
    
    if st.button(f"Genera Scheda Tecnica con {provider}"):
        with st.spinner("Elaborazione tecnica..."):
            prompt = f"""
            Scheda tecnica dettagliata per il format: "{st.session_state.selected_concept}".
            Tema: {activity_input}. Vibe: {vibes_input}.
            Output richiesto in Markdown ben formattato.
            NO Acronimi.
            """
            st.session_state.assets = call_ai(provider, selected_model, api_key, prompt, json_mode=False)

if st.session_state.assets:
    with st.expander("📝 VEDI SCHEDA TECNICA", expanded=True):
        st.markdown(st.session_state.assets)

# FASE 3
if st.session_state.assets:
    st.header("Fase 3: Sales Pitch 💼")
    if st.button("Genera Slide"):
        with st.spinner("Writing pitch..."):
            p_pitch = f"Sales pitch per '{st.session_state.selected_concept}'. Target HR. Prezzo {rrp}."
            pitch_res = call_ai(provider, selected_model, api_key, p_pitch, json_mode=False)
            
            st.markdown(pitch_res)
            st.download_button("Scarica Pitch", pitch_res, "pitch.txt")

st.markdown("---")
st.caption("Timmy Wonka v2.11 (Large Main Prompt) - Powered by Teambuilding.it")
