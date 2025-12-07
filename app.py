import streamlit as st
import google.generativeai as genai
from openai import OpenAI

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Timmy Wonka | R&D Lab",
    page_icon="🎩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STILI CSS (ESTETICA) ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; color: #6C3483; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .success-box { padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIONE SICUREZZA & LOGIN ---
# Inizializza lo stato di autenticazione se non esiste
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    """Controlla la password confrontandola con i secrets."""
    entered_password = st.session_state.password_input
    
    try:
        # Tenta di recuperare la password vera dai secrets
        secret_password = st.secrets["login_password"]
    except (FileNotFoundError, KeyError):
        st.error("⚠️ ERRORE CONFIGURAZIONE: File .streamlit/secrets.toml mancante o chiave 'login_password' non trovata.")
        st.stop()

    if entered_password == secret_password:
        st.session_state.authenticated = True
        del st.session_state.password_input # Pulizia sicurezza
    else:
        st.error("🚫 Password Errata. Riprova.")

# LOGIC GATE: Se NON sei autenticato, mostra solo il login e FERMATI.
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Timmy Wonka R&D")
        st.markdown("Area riservata al team di **Teambuilding.it**.")
        st.info("Inserisci la password per accedere al laboratorio.")
        
        st.text_input(
            "Password", 
            type="password", 
            key="password_input", 
            on_change=check_password
        )
        st.markdown("*Accesso protetto via Streamlit Secrets*")
    
    st.stop() # <--- QUESTO È IL COMANDO FONDAMENTALE. BLOCCA TUTTO IL RESTO.

# ==============================================================================
# DA QUI IN POI IL CODICE VIENE ESEGUITO SOLO SE SEI LOGGATO
# ==============================================================================

# --- 4. IL CERVELLO DI TIMMY (SYSTEM PROMPT) ---
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

OUTPUT RICHIESTI:
Segui le istruzioni dell'utente per FASE 1 (Concept), FASE 2 (Scheda Tecnica & Asset), FASE 3 (Slide Vendita).
"""

# --- 5. FUNZIONE CHIAMATA AI ---
def call_ai(provider, api_key, model_name, prompt):
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    try:
        if provider == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(full_prompt)
            return response.text

        elif provider == "OpenAI / GPT":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        elif provider == "Groq":
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        elif provider == "Grok (xAI)":
            return "⚠️ Integrazione Grok xAI in arrivo. Usa un altro modello."

    except Exception as e:
        return f"❌ ERRORE API: {str(e)}"

# --- 6. SIDEBAR (CONFIGURAZIONE) ---
with st.sidebar:
    st.title("🏭 Fabbrica R&D")
    st.markdown('<div class="success-box">✅ Login Effettuato</div>', unsafe_allow_html=True)
    
    # Logout Button
    if st.button("Logout 🔒"):
        st.session_state.authenticated = False
        st.rerun() # Ricarica la pagina per mostrare il login

    st.divider()

    # Setup AI
    st.subheader("1. Intelligenza")
    provider = st.selectbox("Provider", ["Google Gemini", "OpenAI / GPT", "Groq", "Grok (xAI)"])
    api_key = st.text_input("API Key", type="password")
    
    # Selezione Modello
    model_name = "gemini-1.5-pro-latest"
    if provider == "Google Gemini":
        model_name = st.selectbox("Modello", ["gemini-1.5-pro-latest", "gemini-1.5-flash"])
    elif provider == "OpenAI / GPT":
        model_name = st.selectbox("Modello", ["gpt-4o", "gpt-4-turbo"])
    elif provider == "Groq":
        model_name = st.selectbox("Modello", ["llama3-70b-8192", "mixtral-8x7b-32768"])

    st.divider()

    # Budget Control
    st.subheader("2. Budget Control")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        capex = st.number_input("CAPEX (€)", value=2000, help="Investimento Una Tantum")
    with col_b2:
        opex = st.number_input("OPEX (€/pax)", value=15, help="Costo vivo a persona")
    rrp = st.number_input("Prezzo Vendita (€/pax)", value=120)

    st.divider()

    # Parametri Evento
    st.subheader("3. Parametri")
    pax_range = st.slider("Partecipanti", 10, 500, (30, 100))
    tech_level = st.select_slider("Tech Level", options=["Low Tech", "Hybrid", "High Tech"])
    location = st.selectbox("Location", ["Indoor", "Outdoor", "Ibrido", "Remoto"])

# --- 7. CORPO PRINCIPALE APP ---
st.title("🎩 Timmy Wonka: Generatore di Format")
st.markdown(f"**Status:** Attivo | **Target:** Vendita a €{rrp}/pax | **Budget:** CAPEX €{capex} / OPEX €{opex}")

# Gestione Fasi (Session State)
if "phase" not in st.session_state: st.session_state.phase = 1
if "concepts" not in st.session_state: st.session_state.concepts = ""
if "selected_concept" not in st.session_state: st.session_state.selected_concept = ""
if "assets" not in st.session_state: st.session_state.assets = ""

# --- FASE 1: IDEAZIONE ---
st.header("Fase 1: Ideazione Concept 💡")
activity_input = st.text_input("Su cosa lavoriamo oggi?", placeholder="Es. Cena con delitto, Gara droni, Pittura collaborativa...")

if st.button("Inventa 3 Concept", type="primary"):
    if not api_key:
        st.warning("⚠️ Inserisci la API Key nella sidebar prima di procedere!")
    else:
        with st.spinner("Timmy sta mescolando gli ingredienti..."):
            prompt_f1 = f"""
            ESEGUI FASE 1.
            Tema: {activity_input}
            Budget CAPEX: {capex}€ | OPEX: {opex}€/pax | RRP: {rrp}€/pax
            Pax: {pax_range} | Tech: {tech_level} | Location: {location}
            Dammi 3 concept distinti con Titolo, Hook, Meccanica e Fattibilità.
            """
            response = call_ai(provider, api_key, model_name, prompt_f1)
            st.session_state.concepts = response
            st.session_state.phase = 1

if st.session_state.concepts:
    st.markdown("### 📝 I Concept Proposti")
    st.markdown(st.session_state.concepts)
    st.divider()
    st.info("Copia il TITOLO del concept migliore qui sotto:")
    st.session_state.selected_concept = st.text_input("Titolo Concept Scelto", value=st.session_state.selected_concept)

# --- FASE 2: PRODUZIONE ---
if st.session_state.selected_concept:
    st.header("Fase 2: Produzione Asset & Scheda Tecnica 🛠️")
    st.write(f"Progetto attivo: **{st.session_state.selected_concept}**")
    
    if st.button("Genera Materiali di Gioco"):
        if not api_key:
            st.warning("⚠️ Manca la API Key")
        else:
            with st.spinner("Creazione prototipo in corso..."):
                prompt_f2 = f"""
                ESEGUI FASE 2 per: "{st.session_state.selected_concept}".
                Tema Base: {activity_input}.
                Output: SCHEDA TECNICA (Trama/Regole, Lista Spesa CAPEX {capex}€, Lista OPEX {opex}€, Staff, Asset Narrativi, 3 Prompt Visivi).
                """
                response_f2 = call_ai(provider, api_key, model_name, prompt_f2)
                st.session_state.assets = response_f2
                st.session_state.phase = 2

if st.session_state.assets:
    with st.expander("📂 VEDI SCHEDA TECNICA (Clicca per aprire)", expanded=True):
        st.markdown(st.session_state.assets)

# --- FASE 3: VENDITA ---
if st.session_state.phase >= 2 and st.session_state.assets:
    st.header("Fase 3: Sales Pitch 💼")
    if st.button("Genera Slide Deck"):
        if not api_key:
             st.warning("⚠️ Manca la API Key")
        else:
            with st.spinner("Preparazione pitch commerciale..."):
                prompt_f3 = f"""
                ESEGUI FASE 3 per: "{st.session_state.selected_concept}".
                Target: HR Director. Prezzo: {rrp}€ pax.
                Crea testo per 6 Slide (Titolo, Problema, Soluzione, Timeline, Benefit, Prezzo).
                """
                response_f3 = call_ai(provider, api_key, model_name, prompt_f3)
                st.markdown("### 📊 Pitch Commerciale")
                st.markdown(response_f3)
                st.download_button("Scarica Slide (.txt)", data=response_f3, file_name=f"Pitch_{st.session_state.selected_concept}.txt")

st.markdown("---")
st.caption("Timmy Wonka v1.0 - Teambuilding.it Internal Tool")
