import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic
import aiversion
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 0. GESTIONE DATABASE (GOOGLE SHEETS) ---
SHEET_NAME = "TimmyWonka_DB"

def get_db_connection():
    """Connette al Google Sheet usando i Secrets."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            # Fix per i newline nelle chiavi private
            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet
        else:
            return None
    except Exception as e:
        st.error(f"❌ Errore DB: {e}")
        return None

def load_db_ideas():
    """Legge tutte le idee dal foglio."""
    sheet = get_db_connection()
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

def save_to_gsheet(title, theme, vibe, author, full_concept):
    """Scrive una nuova riga nel foglio."""
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

# --- 2. STILI CSS ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; color: #6C3483; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .success-box { padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 10px; font-weight: bold;}
    .db-box { border: 1px solid #34A853; padding: 15px; border-radius: 10px; background-color: #e6f4ea; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIONE SICUREZZA & LOGIN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    try:
        secret_password = st.secrets["login_password"]
    except (FileNotFoundError, KeyError):
        st.error("⚠️ ERRORE: Configurazione mancante nei Secrets!")
        st.stop()

    if "password_input" in st.session_state:
        if st.session_state.password_input == secret_password:
            st.session_state.authenticated = True
            del st.session_state.password_input
        else:
            st.error("🚫 Password Errata.")

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Timmy Wonka R&D")
        st.info("Inserisci la password per accedere.")
        st.text_input("Password", type="password", key="password_input", on_change=check_password)
        st.button("Entra 🔓", on_click=check_password)
    st.stop()

# ==============================================================================
# LOGICA AI (AGGIORNATA SENZA ACRONIMI)
# ==============================================================================

SYSTEM_PROMPT = """
SEI TIMMY WONKA, Direttore R&D di Teambuilding.it.
Utenti: Team builder PRO (20+ anni exp). Non spiegare l'ovvio. Sii tecnico, creativo e orientato al business.

IL TUO COMPITO:
Sviluppare format di team building reali, scalabili e ad alto margine.

REGOLE DI LINGUAGGIO (IMPORTANTE):
- NON usare MAI acronimi tecnici aziendali come CAPEX, OPEX o RRP nelle tue risposte.
- Usa sempre termini estesi e chiari in italiano, ad esempio: "Costi Fissi/Una Tantum", "Costi Variabili per persona", "Prezzo di Vendita".

REGOLE SUL BUDGET:
- Se i valori sono 0, ignora i vincoli economici e punta sulla massima creatività (Budget Libero).
- Se specificati, rispetta RIGOROSAMENTE i limiti indicati.

TONO:
Creativo (Wonka) ma Logisticamente Spietato (Timmy).
"""

def call_ai(provider, model_id, api_key, prompt):
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    try:
        if provider == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_id)
            response = model.generate_content(full_prompt)
            return response.text
        elif provider == "ChatGPT":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        elif provider == "Claude (Anthropic)":
            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model=model_id, max_tokens=4000, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        elif provider == "Groq":
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        elif provider == "Grok (xAI)":
            client = OpenAI(base_url="https://api.x.ai/v1", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"❌ ERRORE API ({provider} - {model_id}): {str(e)}"

# ==============================================================================
# INTERFACCIA
# ==============================================================================

# --- SETUP AI ---
with st.expander("🧠 Configurazione Cervello AI & Versioni", expanded=True):
    col_ai1, col_ai2, col_ai3 = st.columns([1, 1, 2])
    with col_ai1:
        provider = st.selectbox("1. Scegli Provider", ["Google Gemini", "ChatGPT", "Claude (Anthropic)", "Groq", "Grok (xAI)"])
    with col_ai2:
        api_key = ""
        key_map = {"Google Gemini": "GOOGLE_API_KEY", "ChatGPT": "OPENAI_API_KEY", "Claude (Anthropic)": "ANTHROPIC_API_KEY", "Groq": "GROQ_API_KEY", "Grok (xAI)": "XAI_API_KEY"}
        secret_key_name = key_map[provider]
        if secret_key_name in st.secrets:
            api_key = st.secrets[secret_key_name]
        else:
            api_key = st.text_input("Inserisci API Key", type="password")
    with col_ai3:
        available_models = []
        if api_key:
            if provider == "Google Gemini": available_models = aiversion.get_gemini_models(api_key)
            elif provider == "ChatGPT": available_models = aiversion.get_openai_models(api_key)
            elif provider == "Claude (Anthropic)": available_models = aiversion.get_anthropic_models(api_key)
            elif provider == "Groq": available_models = aiversion.get_openai_models(api_key, base_url="https://api.groq.com/openai/v1")
            elif provider == "Grok (xAI)": available_models = aiversion.get_openai_models(api_key, base_url="https://api.x.ai/v1")
        
        if not available_models or "Errore" in available_models[0]:
             selected_model = st.text_input("Versione (Manuale)")
        else:
            selected_model = st.selectbox("2. Seleziona Versione", available_models)

st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🆕 Nuovo Format")
    
    # 1. VIBE
    st.subheader("1. Vibe & Keywords 🎨")
    vibes_input = st.text_area("Stile", placeholder="Es. Lusso, Adrenalinico...", height=150)
    
    st.divider()
    
    # 2. LOGISTICA
    st.subheader("2. Logistica 📦")
    tech_level = st.select_slider("Livello Tech", ["Low Tech", "Hybrid", "High Tech"])
    phys_level = st.select_slider("Livello Fisico", ["Sedentario", "Leggero", "Attivo"])
    
    st.markdown("**Location (Seleziona):**")
    location_list = []
    if st.checkbox("Indoor", value=True): location_list.append("Indoor")
    if st.checkbox("Outdoor"): location_list.append("Outdoor")
    if st.checkbox("Durante i pasti (Dinner Game)"): location_list.append("Durante i pasti (Dinner Game)")
    if st.checkbox("Ibrido"): location_list.append("Ibrido")
    if st.checkbox("Remoto"): location_list.append("Remoto")
    
    st.divider()
    
    # 3. BUDGET
    st.subheader("3. Budget Control 💰")
    st.caption("Lascia a 0 per nessun limite.")
    capex = st.number_input("Costo una tantum (€)", value=0, help="Costi fissi iniziali (attrezzature, materiali riutilizzabili)")
    opex = st.number_input("Costo materiali a persona (€)", value=0, help="Costi variabili per ogni partecipante (consumabili)")
    rrp = st.number_input("Costo di vendita a persona (€)", value=0, help="Prezzo al cliente finale")

# --- MAIN ---
st.title("🎩💡🎯 Timmy Wonka e la fabbrica dei Format 🏆🧠💰")
st.caption(f"Motore: {selected_model} | Database: Google Sheets (Persistente)")

if "concepts" not in st.session_state: st.session_state.concepts = ""
if "selected_concept" not in st.session_state: st.session_state.selected_concept = ""
if "assets" not in st.session_state: st.session_state.assets = ""
if "idea_saved" not in st.session_state: st.session_state.idea_saved = False

# --- ARCHIVIO GOOGLE SHEETS ---
with st.expander("📂 Archivio Idee (Google Sheets Cloud)", expanded=False):
    if st.button("🔄 Aggiorna Lista dal Cloud"):
        st.rerun()
        
    saved_ideas = load_db_ideas()
    if not saved_ideas:
        st.info("Database vuoto o non connesso.")
    else:
        titles = [i.get('Titolo', 'Senza titolo') for i in saved_ideas if isinstance(i, dict)]
        selected_db_title = st.selectbox("Seleziona un'idea da approfondire:", ["-- Scegli --"] + titles)
        
        if selected_db_title != "-- Scegli --":
            idea_data = next(i for i in saved_ideas if i.get('Titolo') == selected_db_title)
            st.markdown(f"**Tema:** {idea_data.get('Tema')} | **Vibe:** {idea_data.get('Vibe')}")
            st.caption(f"Data: {idea_data.get('Data')} | AI usata: {idea_data.get('Autore')}")
            
            if st.button("🔽 Carica per Approfondimento"):
                st.session_state.selected_concept = idea_data.get('Titolo')
                st.success(f"Caricato: {idea_data.get('Titolo')}")

# FASE 1
st.header("Fase 1: Ideazione Concept 💡")
activity_input = st.text_input("Tema Base dell'Attività", placeholder="Es. Cena con delitto...")

if st.button("Inventa 3 Concept", type="primary"):
    with st.spinner(f"Timmy ({selected_model}) sta elaborando..."):
        loc_str = ", ".join(location_list) if location_list else "Qualsiasi"
        
        # LOGICA BUDGET E NO ACRONIMI
        if capex == 0 and opex == 0 and rrp == 0:
            budget_str = "NESSUN VINCOLO DI BUDGET (Open Budget). Ignora i costi e focalizzati sulla creatività pura."
        else:
            budget_str = f"VINCOLI DI BUDGET: Costi Fissi Max {capex}€, Costi Variabili Max {opex}€/pax, Prezzo Vendita {rrp}€/pax."

        prompt = f"""
        ESEGUI FASE 1. 
        Tema: {activity_input}
        Vibe: {vibes_input if vibes_input else "Libero"}
        
        BUDGET DA RISPETTARE: 
        {budget_str}
        
        LOGISTICA: 
        Tech: {tech_level}
        Fisicità: {phys_level}
        Location supportate: {loc_str}.
        
        Dammi 3 concept distinti. RICORDA: Niente acronimi (Capex/Opex), usa descrizioni italiane.
        """
        response = call_ai(provider, selected_model, api_key, prompt)
        st.session_state.concepts = response
        st.session_state.idea_saved = False

if st.session_state.concepts:
    st.markdown(st.session_state.concepts)
    st.divider()
    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        st.info("Copia qui sotto il titolo del concept che vuoi salvare:")
        st.session_state.selected_concept = st.text_input("Titolo Scelto", value=st.session_state.selected_concept)
    with col_sel2:
        st.markdown("<br>", unsafe_allow_html=True)
        # PULSANTE SALVA SEMPRE VISIBILE
        if st.button("☁️ Salva su Google Sheet", use_container_width=True):
            if not st.session_state.selected_concept:
                st.error("⚠️ Scrivi prima un titolo nel box a sinistra!")
            else:
                with st.spinner("Salvataggio in corso..."):
                    success = save_to_gsheet(
                        st.session_state.selected_concept, 
                        activity_input, 
                        vibes_input, 
                        f"{provider} ({selected_model})",
                        st.session_state.concepts
                    )
                    if success:
                        st.success("✅ Salvato nel DB!")
                        st.session_state.idea_saved = True
                    else:
                        st.warning("⚠️ Già presente o Errore!")
        
        if st.session_state.idea_saved:
            st.caption("✅ Idea archiviata")

# FASE 2
if st.session_state.selected_concept:
    st.header("Fase 2: Scheda Tecnica 🛠️")
    st.markdown(f"Lavorando su: **{st.session_state.selected_concept}**")
    btn_label = f"🚀 Approfondisci con {provider} ({selected_model})"
    if st.button(btn_label):
        with st.spinner("Progettazione..."):
            prompt = f"""
            ESEGUI FASE 2 per: "{st.session_state.selected_concept}". 
            Tema Originale: {activity_input}. Vibe: {vibes_input}.
            Output: SCHEDA TECNICA COMPLETA.
            RICORDA: Usa "Costi Fissi", "Costi Variabili", "Prezzo Vendita". NIENTE CAPEX/OPEX.
            """
            response = call_ai(provider, selected_model, api_key, prompt)
            st.session_state.assets = response

if st.session_state.assets:
    with st.expander("📂 VEDI SCHEDA TECNICA", expanded=True):
        st.markdown(st.session_state.assets)

# FASE 3
if st.session_state.assets:
    st.header("Fase 3: Sales Pitch 💼")
    if st.button("Genera Slide"):
        with st.spinner("Creazione pitch..."):
            prompt = f"""
            ESEGUI FASE 3 per: '{st.session_state.selected_concept}'. 
            Target: HR. Prezzo: {rrp}€. Vibe: {vibes_input}.
            RICORDA: Linguaggio chiaro, niente acronimi tecnici.
            """
            response = call_ai(provider, selected_model, api_key, prompt)
            st.markdown(response)
            
            # PULSANTE DOWNLOAD
            st.download_button(
                label="Scarica Slide (.txt)", 
                data=response, 
                file_name="pitch_format.txt",
                mime="text/plain"
            )

st.markdown("---")
st.caption("Timmy Wonka v2.4 (Fix Syntax) - Powered by Teambuilding.it")
