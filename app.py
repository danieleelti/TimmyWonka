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
from streamlit_extras.copy_to_clipboard import copy_to_clipboard 

# --- FUNZIONE HELPER PER IL NOME DEL FILE ---
def sanitize_filename(title):
    """Rimuove caratteri non validi e spazi per creare un nome di file pulito."""
    return re.sub(r'[^\w\-_]', '', title.replace(' ', '_')) 

# --- 0. GESTIONE DATABASE (GOOGLE SHEETS) ---
SHEET_NAME = "TimmyWonka_DB"
CATALOG_SHEET_TITLE = "CatalogoCompleto" 

def get_db_connection(worksheet_index=0):
    """Restituisce la connessione a una specifica scheda."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client.open(SHEET_NAME).get_worksheet(worksheet_index)
        return None
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def load_db_ideas():
    sheet = get_db_connection(worksheet_index=0)
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

def load_catalog_titles():
    """Carica solo Titoli e Temi dal Catalogo Completo per il prompt AI."""
    try:
        sheet = get_db_connection(worksheet_index=1) 
        if sheet:
            titles = sheet.col_values(1)[1:] if sheet.col_values(1) else []
            themes = sheet.col_values(2)[1:] if sheet.col_values(2) else []
            
            catalog_list = [f"Titolo: {t}, Tema: {th}" for t, th in zip(titles, themes) if t and th]
            
            return catalog_list
        return []
    except Exception as e:
        print(f"Errore caricamento Catalogo: {e}")
        return None


def save_to_gsheet(title, description, vibe, author, full_concept):
    sheet = get_db_connection(worksheet_index=0)
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
            row = [title, description, vibe, date_str] 
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
Obiettivo: Sviluppare Format di team building divertenti, basati sul gioco (gamification e ludico), reali, scalabili e ad alto margine.
IMPORTANTE: Non usare mai acronimi tecnici (Capex/Opex) nelle risposte. Usa "Costi Fissi", "Costi Variabili".
"""

def clean_json_text(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text)
        text = re.sub(r"```$", "", text)
    return text.strip()


def call_ai(provider, model_id, api_key, prompt, history=None, json_mode=False):
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if history:
        for role, content in history:
            messages.append({"role": role, "content": content})
    
    messages.append({"role": "user", "content": prompt})
    
    if json_mode:
        # ISTRUZIONE RAFFORZATA per output JSON
        json_instruction = """
        RISPONDI ESCLUSIVAMENTE CON UN ARRAY JSON VALIDO con esattamente 2 oggetti. 
        NON includere testo introduttivo, commenti, o delimitatori di codice (```json). 
        Il tuo output DEVE iniziare e finire con le parentesi quadre dell'array JSON [].
        [{"titolo":"...", "descrizione":"..."}].
        """
        messages[-1]["content"] += "\n" + json_instruction


    try:
        text_response = ""
        
        if provider in ["ChatGPT", "Groq", "Grok (xAI)"]:
            base_url = None
            if provider == "Groq": base_url="https://api.groq.com/openai/v1"
            elif provider == "Grok (xAI)": base_url="https://api.x.ai/v1"
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model_id, 
                messages=messages
            )
            text_response = response.choices[0].message.content
            
        elif provider == "Google Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_id)
            
            final_prompt = "\n".join([f"[{m['role'].upper()}]: {m['content']}" for m in messages[1:]])
            response = model.generate_content(final_prompt)
            
            if not response.candidates:
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason.name
                    return f"❌ CONTENUTO BLOCCATO DA GEMINI. Motivo: Il prompt o l'output hanno violato le policy di sicurezza di Google (Motivo: {block_reason}). Riprova con un prompt meno sensibile."
                else:
                    return "❌ ERRORE GEMINI SCONOSCIUTO: Nessun candidato restituito."
            
            text_response = response.text
        
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

def generate_technical_sheet(concept_title, activity_input, vibes_input, provider, selected_model, api_key):
    """Funzione che inizializza la Fase 2 e la chat history."""
    
    initial_prompt = f"""
    Genera la Scheda Tecnica dettagliata per il format: "{concept_title}".
    Tema Originale: {activity_input}. Vibe: {vibes_input}.
    
    Output richiesto: Scheda Tecnica completa, formattata in Markdown.
    IMPORTANTE: La descrizione deve focalizzarsi ESCLUSIVAMENTE sulle dinamiche, l'esperienza utente e la logistica. 
    NON includere analisi di costi/benefici, prezzi, o calcoli finanziari.
    NO Acronimi.
    """
    
    st.session_state.assets = call_ai(provider, selected_model, api_key, initial_prompt, json_mode=False)
    
    st.session_state.phase2_history = [
        ("user", "Inizio Fase 2: Richiesta Scheda Tecnica Dettagliata."),
        ("assistant", st.session_state.assets)
    ]

def handle_refinement_turn(comment):
    """Gestisce un turno di chat, aggiorna la history e l'asset principale."""
    
    st.session_state.phase2_history.append(("user", comment))

    history_messages = st.session_state.phase2_history 
    
    is_final_summary_request = "riassunto" in comment.lower() or "finale" in comment.lower() or "salvare" in comment.lower()

    if is_final_summary_request:
        last_prompt = f"""
        L'utente sta chiedendo un riassunto finale o un documento da salvare. 
        Basandoti sulla Scheda Tecnica attuale (che è il contenuto della penultima risposta dell'assistente nella history), genera un documento di riepilogo pulito e finale in Markdown. 
        L'output deve essere SOLO il documento di riepilogo/conclusione.
        """
    else:
        last_prompt = f"""
        Rispondi alla richiesta dell'utente. Se l'utente chiede una modifica alla Scheda Tecnica, ricreala interamente con le revisioni richieste. Se l'utente chiede un nuovo materiale (es. lista di controllo, pitch), produci quel materiale.
        L'output deve essere SOLO il contenuto richiesto in Markdown.
        MANTIENI IL FOCUS SULLE DINAMICHE: NON INCLUDERE COSTI O ANALISI FINANCIARIE.
        """
    
    new_response = call_ai(
        st.session_state.provider, 
        st.session_state.selected_model, 
        st.session_state.api_key, 
        last_prompt, 
        history=history_messages,
        json_mode=False
    )
    
    st.session_state.phase2_history.append(("assistant", new_response))
    st.session_state.assets = new_response


# ==============================================================================
# INTERFACCIA
# ==============================================================================

# --- SETUP ---
with st.expander("🧠 Configurazione Cervello AI", expanded=True):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: 
        provider = st.selectbox("Provider", ["Google Gemini", "ChatGPT", "Claude (Anthropic)", "Groq", "Grok (xAI)"])
        st.session_state.provider = provider
    
    with c2:
        key_map = {"Google Gemini": "GOOGLE_API_KEY", "ChatGPT": "OPENAI_API_KEY", "Claude (Anthropic)": "ANTHROPIC_API_KEY", "Groq": "GROQ_API_KEY", "Grok (xAI)": "XAI_API_KEY"}
        secret_key_name = key_map[provider]
        
        if secret_key_name in st.secrets:
            api_key = st.secrets[secret_key_name]
        else:
            api_key = st.text_input("Inserisci API Key", type="password")
        st.session_state.api_key = api_key
    
    with c3:
        models = []
        if api_key:
            try:
                if provider == "Google Gemini": models = aiversion.get_gemini_models(api_key)
                elif provider == "ChatGPT": models = aiversion.get_openai_models(api_key)
                elif provider == "Claude (Anthropic)": models = aiversion.get_anthropic_models(api_key)
                elif provider == "Groq": 
                    try:
                        models = aiversion.get_openai_models(api_key, base_url="https://api.groq.com/openai/v1")
                    except:
                        models = ["llama3-8b-8192", "llama3-70b-8192"]
                        st.warning("⚠️ Elenco modelli Groq non disponibile. Caricati modelli standard.")
                elif provider == "Grok (xAI)": models = aiversion.get_openai_models(api_key, base_url="https://api.x.ai/v1")
            except:
                models = []
        
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
        st.session_state.selected_model = selected_model


st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🆕 Nuovo Format")
    
    st.subheader("1. Vibe & Keywords 🎨")
    vibes_input = st.text_input("Stile", placeholder="Lusso, Adrenalinico, Vintage...") 
    st.session_state.vibes_input = vibes_input
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
if "autogenerate_assets" not in st.session_state: st.session_state.autogenerate_assets = False
if "phase2_history" not in st.session_state: st.session_state.phase2_history = []


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
                st.session_state.autogenerate_assets = True 
                st.rerun() 

# FASE 1
st.header("Fase 1: Ideazione 💡")
activity_input = st.text_area("Tema Base", placeholder="Es. Robot Wars, La caccia al tesoro...", height=150)
st.session_state.activity_input = activity_input

if st.button("✨ Inventa 2 Idee", type="primary"):
    with st.spinner("Brainstorming..."):
        
        budget_str = "Libero" if (capex+opex+rrp)==0 else f"Fissi {capex}€, Var {opex}€, Vendita {rrp}€"
        
        prompt = f"""
        Genera 2 concept distinti per: {activity_input}. 
        Vibe: {vibes_input}. Budget: {budget_str}. 
        Logistica: {tech_level}, {phys_level}, {', '.join(locs)}.
        
        [Rimosso il contesto del Catalogo Completo per la velocità. Ora inventa liberamente.]
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
            concept_title = concept.get('titolo', concept.get('title', 'Senza Titolo'))
            concept_description = concept.get('descrizione', concept.get('description', 'Nessuna descrizione fornita dall\'AI.'))
            
            st.subheader(f"{idx+1}. {concept_title}")
            st.markdown(concept_description)
            
            c1, c2, c3 = st.columns([1, 1, 1])
            
            if c1.button("🚀 Approfondisci", key=f"app_{idx}"):
                st.session_state.selected_concept = concept_title
                st.session_state.assets = ""
                st.session_state.autogenerate_assets = True 
                st.rerun()
            
            if c2.button("💾 Salva per dopo", key=f"save_{idx}"):
                res = save_to_gsheet(concept_title, concept_description, vibes_input, f"{provider}", str(concept)) 
                if res: st.toast(f"✅ Salvato: {concept_title}")
                else: st.toast("⚠️ Già nel DB")

            if c3.button("🔄 Rigenera (Boccia)", key=f"regen_{idx}"):
                with st.spinner(f"Rimpiazzo l'idea {idx+1}..."):
                    p_regen = f"""
                    L'utente ha scartato l'idea "{concept_title}". 
                    Genera 1 NUOVO concept alternativo per il tema {activity_input}.
                    Stessi vincoli.
                    """
                    new_concept = call_ai(provider, selected_model, api_key, p_regen, json_mode=True)
                    if isinstance(new_concept, list) and len(new_concept) > 0:
                        st.session_state.concepts_list[idx] = new_concept[0]
                        st.rerun()

# FASE 2: LOGICA DI GENERAZIONE AUTOMATICA E CHAT
if st.session_state.selected_concept:
    st.divider()
    st.header(f"Fase 2: Deep Dive e Refinement 🛠️")
    st.subheader(f"Lavorando su: '{st.session_state.selected_concept}'")

    if st.session_state.autogenerate_assets:
        generate_technical_sheet(
            st.session_state.selected_concept, 
            st.session_state.activity_input, 
            st.session_state.vibes_input, 
            st.session_state.provider, 
            st.session_state.selected_model, 
            st.session_state.api_key
        )
        st.session_state.autogenerate_assets = False 

    if st.session_state.assets:
        
        st.info(f"L'ultimo output di Timmy Wonka è salvato come asset finale. Per modificarlo, usa la chat qui sotto.")
        
        with st.expander("📝 VEDI ULTIMO ASSET PRODOTTO", expanded=False):
            st.markdown(st.session_state.assets)

        st.subheader("Chat di Refinement 💬")
        
        for role, content in st.session_state.phase2_history:
            if role == "user":
                st.chat_message("user").markdown(content)
            elif role == "assistant":
                st.chat_message("assistant").markdown(content)

        # Controlli Chat e Salvataggio
        col_chat, col_save, col_copy = st.columns([3, 1, 1])
        
        comment_input = st.text_area(
            "Chiedi a Timmy Wonka una modifica, un approfondimento o un riassunto finale da salvare:", 
            key="comment_input", 
            height=100
        )
        
        if col_chat.button("💬 Invia Richiesta / Continua la Chat", use_container_width=True):
            if comment_input:
                with st.spinner("Timmy sta elaborando la richiesta..."):
                    handle_refinement_turn(comment_input) 
                    del st.session_state.comment_input 
                    st.rerun()
            else:
                st.warning("Scrivi un commento o una richiesta!")

        if col_save.button("💾 Salva Versione Finale", type="primary", use_container_width=True):
            
            final_title = st.session_state.selected_concept
            final_description = st.session_state.assets 
            original_vibe = st.session_state.vibes_input
            
            res = save_to_gsheet(
                final_title, 
                final_description, 
                original_vibe, 
                st.session_state.provider, 
                "Final Version"
            )
            
            if res: st.success(f"✅ Versione finale di '{final_title}' salvata nel DB!")
            else: st.error("⚠️ Errore nel salvataggio o idea già presente.")
            
        
        file_name = f"{sanitize_filename(st.session_state.selected_concept)}_Final.txt"
        col_copy.download_button(
            label="⬇️ Scarica Ultimo Asset (.txt)", 
            data=st.session_state.assets, 
            file_name=file_name, 
            mime="text/plain",
            use_container_width=True
        )


# FASE 3
if st.session_state.assets:
    st.divider()
    st.header("Fase 3: Sales Pitch 💼")
    if st.button("Genera Slide"):
        with st.spinner("Writing pitch..."):
            p_pitch = f"Sales pitch per '{st.session_state.selected_concept}'. Target HR. Prezzo {rrp}."
            pitch_res = call_ai(st.session_state.provider, st.session_state.selected_model, st.session_state.api_key, p_pitch, history=st.session_state.phase2_history, json_mode=False)
            
            st.markdown(pitch_res)
            file_name_pitch = f"{sanitize_filename(st.session_state.selected_concept)}_Pitch.txt"
            st.download_button("Scarica Pitch", pitch_res, file_name_pitch)

st.markdown("---")
st.caption("Timmy Wonka v2.31 (Definitive Module Fix) - Powered by Teambuilding.it")
