import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance
import json
import urllib.parse

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Experte", layout="wide")
st.title("🪙 Münz-Detektiv: Systematische Identifikation")

# --- SESSION STATE (Das Gedächtnis der App) ---
# Hier werden die Werte initialisiert, damit sie nicht verloren gehen.
if "ppi" not in st.session_state:
    st.session_state.ppi = 160
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# API-Check
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemma-3-27b')
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. KALIBRIERUNG ---
st.header("📏 1. Kalibrierung & Messung")
st.info("Referenzmünze auflegen, Regler anpassen und Kalibrier-Button drücken.")

col_cal1, col_cal2, col_cal3 = st.columns([2, 1, 1])

with col_cal1:
    size_px = st.slider("Kreisgröße anpassen", 50, 800, 200)

with col_cal2:
    if st.button("📍 Kalibrieren 1 €", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibrierung auf 1 € gespeichert!")

with col_cal3:
    if st.button("📍 Kalibrieren 2 €", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibrierung auf 2 € gespeichert!")

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Aktueller Messwert", f"{mm_ist:.2f} mm")

# Visueller Mittelpunkt
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 20px; background: #1e1e1e; border-radius: 15px;">
        <div style="width:{size_px}px; height:{size_px}px; border:4px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center;">
            <div style="width: 6px; height: 6px; background: red; border-radius: 50%;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. ANALYSE (Aktion) ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Vorschau", width=300)

    # --- HIER PASSIERT DIE ARBEIT ---
    if st.button("🚀 Systematische Bestimmung starten"):
        with st.status("Hierarchische Analyse läuft...", expanded=True) as status:
            prompt = f"""
            Analysiere als Numismatiker. Durchmesser: {mm_ist:.1f} mm.
            HIERARCHISCHE SCHRITTE:
            1. MOTIV-TYP: (Wappen, Adler, Kopf, Figur, etc.)
            2. STRUKTUR: (Blickrichtung, Teilung des Schildes, Haltung der Figur)
            3. FEIN-DETAILS: (Accessoires wie Krone, Zepter, Bart, Haarlänge, Augenbinde, Kind?)
            4. KONTEXT: (Gelesene Zeichen rundherum oder mittig)

            Antworte NUR als JSON:
            {{
              "Identität": "Land, Nominal, Herrscher",
              "Details": "Struktur & Fein-Merkmale",
              "Legende": "Gelesene Zeichen",
              "Keywords": "Suchbegriffe für Fachhandel",
              "Begruendung": "Warum passt das zu {mm_ist:.1f} mm?"
            }}
            """
            try:
                # Bildverbesserung & API-Aufruf
                enhanced = ImageEnhance.Contrast(img).enhance(1.8)
                response = model.generate_content([prompt, enhanced])
                
                # Robustes JSON Parsing (findet den { } Block im Text)
                raw_text = response.text
                json_start = raw_text.find('{')
                json_end = raw_text.rfind('}') + 1
                
                # WICHTIG: Ergebnis im Session State speichern!
                st.session_state.analysis_result = json.loads(raw_text[json_start:json_end])
                
                status.update(label="Analyse fertig!", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")
                with st.expander("Fehler-Details"):
                    st.write(response.text if 'response' in locals() else "Keine Antwort von der API.")

# --- 3. ERGEBNIS-ANZEIGE (Darstellung) ---
# Dieser Teil wird IMMER ausgeführt, wenn ein Ergebnis im "Gedächtnis" ist.
# Er liegt AUSSERHALB des if st.button()-Blocks.
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    st.divider()
    
    # Ergebnisse anzeigen
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.subheader("Befund")
        st.success(f"**Bestimmung:** {res.get('Identität', 'Keine Bestimmung')}")
        st.write(f"**Details:** {res.get('Details', '-')}")
    with col_res2:
        st.subheader("Kontext")
        st.write(f"**Legende:** `{res.get('Legende', '-')}`")
        st.info(f"**Analyse:** {res.get('Begruendung', '-')}")

    # Profi-Links generieren
    st.subheader("🔗 Verifikation")
    search_term = f"{res.get('Identität', '')} {res.get('Keywords', '')} {mm_ist:.1f}mm"
    q = urllib.parse.quote(search_term)
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"[📚 Numista Check](https://en.numista.com/catalogue/index.php?q={q})")
    c2.markdown(f"[💰 MA-Shops Handel](https://www.ma-shops.de/result.php?searchstr={q})")
    c3.markdown(f"[🖼️ Google Bilder](https://www.google.com/search?q={q}&tbm=isch)")
    
    st.caption(f"Generierter Suchbegriff: {search_term}")

    # Button zum Zurücksetzen
    st.divider()
    if st.button("🗑️ Analyse-Ergebnis löschen"):
        st.session_state.analysis_result = None
        st.rerun()
