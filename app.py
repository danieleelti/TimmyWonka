import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic
import aiversion  # Importiamo il modulo per le versioni

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Timmy Wonka | R&D Lab",
    page_icon="🎩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STILI CSS ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; color: #6C3483; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .success-box { padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIONE SICUREZZA & LOGIN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    try:
        secret_password = st.secrets["login_password"]
    except (FileNotFoundError, KeyError):
        st.error("⚠️ ERRORE: Password non configurata nei Secrets!")
        st.stop()

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
    st.stop()

# ==============================================================================
# LOGICA INTELLIGENZA ARTIFICIALE
# ==============================================================================

SYSTEM_PROMPT = """
SEI TIMMY WONKA, Direttore R&D di Teambuilding.it.
Utenti: Team builder PRO (20+ anni exp). Non spiegare l'ovvio. Sii tecnico, creativo e orientato al business.

IL TUO COMPITO:
Sviluppare format di team building reali, scalabili e ad alto margine.

REGOLE SUL BUDGET:
- Rispetta RIGOROSAMENTE i limiti CAPEX (Investimenti Una Tantum) e OPEX (Costi variabili/pax).
- Calcola sempre se il RRP (Prezzo vendita) copre i costi e garantisce margine.

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
                model=model_id,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        elif provider == "Claude (Anthropic)":
            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model=model_id,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

        elif provider == "Groq":
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        elif provider == "Grok (xAI)":
            client = OpenAI(base_url="https://api.x.ai/v1", api_key=api_key)
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

    except Exception as e:
        return f"❌ ERRORE API ({provider} - {model_id}): {str(e)}"

# --- 4. SIDEBAR DINAMICA ---
with st.sidebar:
    st.title("🏭 Fabbrica R&D")
    
    # Bottone Logout semplice
    if st.button("Logout 🔒"):
        st.session_state.authenticated = False
        st.rerun()

    st.divider()

    # --- SELEZIONE PROVIDER ---
    st.subheader("1. Motore AI")
    provider = st.selectbox("Provider", ["Google Gemini", "ChatGPT", "Claude (Anthropic)", "Groq", "Grok (xAI)"])
    
    # Recupero API Key dai secrets
    api_key = ""
    key_map = {
        "Google Gemini": "GOOGLE_API_KEY",
        "ChatGPT": "OPENAI_API_KEY",
        "Claude (Anthropic)": "ANTHROPIC_API_KEY",
        "Groq": "GROQ_API_KEY",
        "Grok (xAI)": "XAI_API_KEY"
    }
    
    secret_key_name = key_map[provider]
    if secret_key_name in st.secrets:
        api_key = st.secrets[secret_key_name]
        st.caption(f"🔑 Key caricata da Secrets")
    else:
        st.warning(f"⚠️ Manca {secret_key_name} nei secrets!")
        api_key = st.text_input("Inserisci API Key manuale", type="password")

    # --- RECUPERO VERSIONI (Chiamata a aiversion.py) ---
    st.write("---")
    st.caption("🔍 Scansione modelli disponibili...")
    
    available_models = []
    
    if api_key:
        if provider == "Google Gemini":
            available_models = aiversion.get_gemini_models(api_key)
        elif provider == "ChatGPT":
            available_models = aiversion.get_openai_models(api_key)
        elif provider == "Claude (Anthropic)":
            available_models = aiversion.get_anthropic_models(api_key)
        elif provider == "Groq":
            available_models = aiversion.get_openai_models(api_key, base_url="https://api.groq.com/openai/v1")
        elif provider == "Grok (xAI)":
            available_models = aiversion.get_openai_models(api_key, base_url="https://api.x.ai/v1")
    
    # Se la lista è vuota o contiene errori, gestisci il fallback
    if not available_models or "Errore" in available_models[0]:
        st.error(f"Impossibile recuperare modelli: {available_models}")
        selected_model = st.text_input("Scrivi ID Modello Manualmente (es. gemini-1.5-pro)")
    else:
        # MENU A TENDINA CON LE VERSIONI REALI
        selected_model = st.selectbox("Seleziona Versione", available_models)

    st.info(f"Usando: **{selected_model}**")

    st.divider()

    # --- BUDGET & PARAMETRI ---
    st.subheader("2. Parametri")
    col1, col2 = st.columns(2)
    with col1: capex = st.number_input("CAPEX (€)", 2000)
    with col2: opex = st.number_input("OPEX (€/pax)", 15)
    rrp = st.number_input("RRP (€/pax)", 120)
    
    pax_range = st.slider("Pax", 10, 500, (30, 100))
    tech_level = st.select_slider("Tech", ["Low", "Hybrid", "High"])
    location = st.selectbox("Location", ["Indoor", "Outdoor", "Ibrido", "Remoto"])

# --- 5. INTERFACCIA PRINCIPALE ---
st.title("🎩 Timmy Wonka e la fabbrica dei Format")

# Gestione Stato
if "phase" not in st.session_state: st.session_state.phase = 1
if "concepts" not in st.session_state: st.session_state.concepts = ""
if "selected_concept" not in st.session_state: st.session_state.selected_concept = ""
if "assets" not in st.session_state: st.session_state.assets = ""

# FASE 1
st.header("Fase 1: Ideazione Concept 💡")
activity_input = st.text_input("Tema Attività", placeholder="Es. Cena con delitto, Robot Wars...")

if st.button("Inventa 3 Concept", type="primary"):
    with st.spinner(f"Timmy (v. {selected_model}) sta elaborando..."):
        prompt = f"""
        ESEGUI FASE 1. Tema: {activity_input}
        Budget: CAPEX {capex}€, OPEX {opex}€/pax, RRP {rrp}€/pax.
        Pax: {pax_range}, Tech: {tech_level}, Loc: {location}.
        Dammi 3 concept distinti.
        """
        response = call_ai(provider, selected_model, api_key, prompt)
        st.session_state.concepts = response

if st.session_state.concepts:
    st.markdown(st.session_state.concepts)
    st.divider()
    st.info("Copia titolo concept:")
    st.session_state.selected_concept = st.text_input("Titolo Concept Scelto", value=st.session_state.selected_concept)

# FASE 2
if st.session_state.selected_concept:
    st.header("Fase 2: Scheda Tecnica 🛠️")
    if st.button("Genera Materiali"):
        with st.spinner("Creazione asset..."):
            prompt = f"""
            ESEGUI FASE 2 per: "{st.session_state.selected_concept}". Tema: {activity_input}.
            Output: SCHEDA TECNICA COMPLETA.
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
            ESEGUI FASE 3 per: "{st.session_state.selected_concept}". Target: HR. Prezzo: {rrp}€.
            Crea testo per 6 Slide.
            """
            response = call_ai(provider, selected_model, api_key, prompt)
            st.markdown(response)
            st.download_button("Scarica Slide (.txt)", data=response, file_name=f"Pitch_{st.session_state.selected_concept}.txt")

st.markdown("---")
st.caption("Timmy Wonka v1.2 - Powered by Teambuilding.it")
