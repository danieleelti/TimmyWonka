import streamlit as st
# Importazioni librerie AI (pseudo-codice)
# from langchain / openai / google.generativeai ...

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Timmy Wonka R&D", layout="wide")

# --- SIDEBAR: I PARAMETRI ---
st.sidebar.title("🏭 Fabbrica delle Idee")

# Selettore AI
selected_model = st.sidebar.selectbox("Scegli il Cervello", ["Gemini 1.5 Pro", "GPT-4o", "Groq (Llama3)", "Claude 3.5"])

# Input Generali
activity_type = st.sidebar.text_input("Tipologia Attività", "Es. Gara di Cucina Molecolare")
target_pax = st.sidebar.slider("Numero Partecipanti", 10, 500, 50)

# Input Budget (Divisi come richiesto)
st.sidebar.markdown("### 💰 Budget Control")
capex = st.sidebar.number_input("Budget CAPEX (Una Tantum - €)", value=1000)
opex = st.sidebar.number_input("Budget OPEX (Consumabili/pax - €)", value=20)
rrp = st.sidebar.number_input("Prezzo Vendita Target (a pax - €)", value=120)

# --- CORPO PRINCIPALE ---
st.title("🎩 Timmy Wonka: L'Inventore di Format")

# Gestione dello stato (Fase 1, 2, 3)
if "phase" not in st.session_state:
    st.session_state.phase = 1

# FASE 1: IDEAZIONE
if st.session_state.phase == 1:
    if st.button("Inventa 3 Concept"):
        # Qui chiamiamo l'AI con il SYSTEM PROMPT + i parametri + "ESEGUI FASE 1"
        # Mostriamo i 3 risultati
        pass

# FASE 2: PRODUZIONE ASSET
if st.session_state.phase == 2:
    st.write(f"Hai scelto il concept: {st.session_state.selected_concept}")
    if st.button("Genera Materiali e Scheda Tecnica"):
        # Chiamata AI: "ESEGUI FASE 2 sul concept scelto"
        # Output lungo: Trama, Liste spesa, Regole...
        pass

# FASE 3: PRESENTAZIONE
if st.session_state.phase == 3:
    if st.button("Crea Slide Deck"):
        # Chiamata AI: "ESEGUI FASE 3"
        pass
