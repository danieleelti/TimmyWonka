import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic
import aiversion  # Il modulo versioni che abbiamo creato

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
    .ai-setup-box { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 20px;}
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
# LOGICA INTELLIGENZA ARTIFICIALE
# ==============================================================================

SYSTEM_PROMPT = """
SEI TIMMY WONKA, Direttore R&D di Teambuilding.it.
Utenti: Team builder PRO (20+ anni exp). Non spiegare l'ovvio. Sii tecnico, creativo e orientato al business.

IL TUO COMPITO:
Sviluppare format di team building reali, scalabili e ad alto margine.

REGOLE SUL BUDGET:
- Rispetta RIGOROSAMENTE i limiti di budget forniti (Costi fissi e variabili).
- Calcola sempre se il prezzo di vendita copre i costi e garantisce margine.

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

# ==============================================================================
# INTERFACCIA UTENTE
# ==============================================================================

# --- SEZIONE SUPERIORE: SETUP AI ---
with st.expander("🧠 Configurazione Cervello AI & Versioni", expanded=True):
    col_ai1, col_ai2, col_ai3 = st.columns([1, 1, 2])
    
    with col_ai1:
        provider = st.selectbox("1. Scegli Provider", ["Google Gemini", "ChatGPT", "Claude (Anthropic)", "Groq", "Grok (xAI)"])

    with col_ai2:
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
            st.markdown(f"<br>✅ **Key Caricata** da Secrets", unsafe_allow_html=True)
        else:
            st.warning(f"Manca {secret_key_name}")
            api_key = st.text_input("Inserisci API Key manuale", type="password")

    with col_ai3:
        available_models = []
        if api_key:
            if provider == "Google Gemini": available_models = aiversion.get_gemini_models(api_key)
            elif provider == "ChatGPT": available_models = aiversion.get_openai_models(api_key)
            elif provider == "Claude (Anthropic)": available_models = aiversion.get_anthropic_models(api_key)
            elif provider == "Groq": available_models = aiversion.get_openai_models(api_key, base_url="https://api.groq.com/openai/v1")
            elif provider == "Grok (xAI)": available_models = aiversion.get_openai_models(api_key, base_url="https://api.x.ai/v1")
        
        if not available_models or "Errore" in available_models[0]:
             selected_model = st.text_input("Versione (Inserimento manuale se lista fallisce)")
        else:
            selected_model = st.selectbox("2. Seleziona Versione Modello", available_models)

st.divider()

# --- SIDEBAR: PARAMETRI & VIBE ---
with st.sidebar:
    # MODIFICA APPLICATA QUI
    st.title("🆕 Nuovo Format")
    
    # 1. Vibe & Keywords
    st.subheader("1. Vibe & Keywords 🎨")
    vibes_input = st.text_area(
        "Stile & Atmosfera", 
        placeholder="Es. Lusso, Adrenalinico, Sostenibile, Cyberpunk, Elegante, Competitivo...", 
        height=150, 
        help="Aggettivi che definiscono l'atmosfera e lo stile del format."
    )

    st.divider()

    # 2. Budget Control (VERTICALE)
    st.subheader("2. Budget Control 💰")
    capex = st.number_input("Costo una tantum (€)", 2000, help="Spese fisse iniziali (es. attrezzatura)")
    opex = st.number_input("Costo materiali a persona (€)", 15, help="Spese variabili per ogni partecipante")
    rrp = st.number_input("Costo di vendita a persona (€)", 120, help="Prezzo al cliente finale")

    st.divider()

    # 3. Logistica (MODIFICATA)
    st.subheader("3. Logistica 📦")
    
    tech_level = st.select_slider("Livello Tech", ["Low Tech", "Hybrid", "High Tech"])
    
    phys_level = st.select_slider("Livello Fisico", ["Sedentario (Mental)", "Leggero (Movimento)", "Attivo (Sport)"])
    
    location = st.selectbox("Location", ["Indoor", "Outdoor", "Durante i pasti (Dinner Game)", "Ibrido", "Remoto"])

# --- CORPO PRINCIPALE ---
st.title("🎩💡🎯 Timmy Wonka e la fabbrica dei Format 🏆🧠💰")
st.caption(f"Motore: {selected_model} | Budget Una Tantum: {capex}€")

# Gestione Stato
if "phase" not in st.session_state: st.session_state.phase = 1
if "concepts" not in st.session_state: st.session_state.concepts = ""
if "selected_concept" not in st.session_state: st.session_state.selected_concept = ""
if "assets" not in st.session_state: st.session_state.assets = ""

# FASE 1: IDEAZIONE
st.header("Fase 1: Ideazione Concept 💡")
activity_input = st.text_input("Tema Base dell'Attività", placeholder="Es. Cena con delitto, Robot Wars, Cooking Class...")

if st.button("Inventa 3 Concept", type="primary"):
    with st.spinner(f"Timmy ({selected_model}) sta elaborando con stile: {vibes_input}..."):
        # PROMPT 
        prompt = f"""
        ESEGUI FASE 1. 
        Tema Base: {activity_input}
        VIBE/KEYWORDS RICHIESTE: {vibes_input if vibes_input else "Standard creativo"}

        Budget: 
        - Costo Una Tantum (CAPEX): {capex}€
        - Costo Materiali a persona (OPEX): {opex}€/pax
        - Prezzo Vendita Target: {rrp}€/pax
        
        Logistica: 
        - Tech Level: {tech_level}
        - Fisicità richiesta: {phys_level}
        - Location: {location}
        
        Dammi 3 concept distinti che rispettino i vibe e la logistica indicata.
        """
        response = call_ai(provider, selected_model, api_key, prompt)
        st.session_state.concepts = response

if st.session_state.concepts:
    st.markdown(st.session_state.concepts)
    st.divider()
    st.info("Copia titolo concept:")
    st.session_state.selected_concept = st.text_input("Titolo Concept Scelto", value=st.session_state.selected_concept)

# FASE 2: PRODUZIONE
if st.session_state.selected_concept:
    st.header("Fase 2: Scheda Tecnica 🛠️")
    if st.button("Genera Materiali"):
        with st.spinner("Creazione asset..."):
            prompt = f"""
            ESEGUI FASE 2 per: "{st.session_state.selected_concept}". 
            Tema Originale: {activity_input}. Vibe: {vibes_input}.
            Output: SCHEDA TECNICA COMPLETA.
            """
            response = call_ai(provider, selected_model, api_key, prompt)
            st.session_state.assets = response

if st.session_state.assets:
    with st.expander("📂 VEDI SCHEDA TECNICA", expanded=True):
        st.markdown(st.session_state.assets)

# FASE 3: VENDITA
if st.session_state.assets:
    st.header("Fase 3: Sales Pitch 💼")
    if st.button("Genera Slide"):
        with st.spinner("Creazione pitch..."):
            prompt = f"""
            ESEGUI FASE 3 per: "{st.session_state.selected_concept}". Target: HR. Prezzo: {rrp}€. Vibe: {vibes_input}.
            Crea testo per 6 Slide.
            """
            response = call_ai(provider, selected_model, api_key, prompt)
            st.markdown(response)
            st.download_button("Scarica Slide (.txt)", data=response, file_name=f"Pitch_{st.session_state.selected_concept}.txt")

st.markdown("---")
st.caption("Timmy Wonka v1.7 - Powered by Teambuilding.it")
