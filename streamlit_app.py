import streamlit as st
from google import genai  # Neue Bibliothek
from PIL import Image, ImageEnhance
import json
import urllib.parse
import io

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Gemma 3", layout="wide")
st.title("🪙 Münz-Detektiv: Systematische Gemma-Analyse")

# Session State Initialisierung
if "ppi" not in st.session_state:
    st.session_state.ppi = 160
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# Neuer Client-Ansatz laut Google Docs
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- 1. KALIBRIERUNG (Zentral im Hauptbereich) ---
st.header("📏 1. Kalibrierung & Messung")
st.info("Referenzmünze auflegen, Regler anpassen und Kalibrier-Button drücken.")

col_cal1, col_cal2, col_cal3 = st.columns([2, 1, 1])

with col_cal1:
    size_px = st.slider("Kreisgröße anpassen", 50, 800, 200)

with col_cal2:
    if st.button("📍 Kalibrieren 1 €", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibrierung auf 1 € (23.25mm) gespeichert!")

with col_cal3:
    if st.button("📍 Kalibrieren 2 €", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibrierung auf 2 € (25.75mm) gespeichert!")

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Aktueller Messwert", f"{mm_ist:.2f} mm")

# Visueller Messkreis
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 20px; background: #1e1e1e; border-radius: 15px;">
        <div style="width:{size_px}px; height:{size_px}px; border:4px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center;">
            <div style="width: 8px; height: 8px; background: red; border-radius: 50%;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. BILD-UPLOAD & ANALYSE ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    st.image(raw_img, caption="Vorschau", width=350)

    if st.button("🚀 Systematische Bestimmung starten"):
        with st.status("Hierarchische Analyse läuft...") as status:
            
            # Bild für die API vorbereiten
            img_byte_arr = io.BytesIO()
            raw_img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # Der hierarchische Prompt
            prompt = f"""
            Analysiere diese Münze streng hierarchisch wie ein Numismatiker. 
            Physische Größe: {mm_ist:.1f} mm.

            SCHRITT 1: MOTIV-TYP
            Bestimme das Hauptmotiv (Wappen, Adler, Gesicht/Portrait, Figur, etc.).

            SCHRITT 2: STRUKTUR-DETAILS
            - Wappen: Teilung (geviertelt/halb), Form des Schildes?
            - Adler: Blickrichtung, Flügelhaltung?
            - Kopf: Profil oder frontal? Bart? Haarlänge? Markante Züge (Nase, Brille)?
            - Figur: Stehend/sitzend? Blickrichtung?

            SCHRITT 3: FEIN-ANALYSE
            - Was wird gehalten (Zepter, Reichsapfel, Kind, Waage, Schwert)?
            - Accessoires (Krone, Heiligenschein, Augenbinde)?
            - Symbole in den Wappenfeldern (Löwen, Streifen, Adler, Kreuze)? Wie oft?

            SCHRITT 4: LEGENDE
            Lies alle Zeichen rundherum und in der Mitte. Setze sie in Kontext zum Motiv.

            Antworte ausschließlich im JSON-Format:
            {{
              "Identitaet": "Land, Nominal, Herrscher/Republik",
              "Motiv_Analyse": "Beschreibung der Struktur und Blickrichtungen",
              "Fein_Details": "Liste aller Symbole und Accessoires",
              "Legende": "Gelesene Zeichen",
              "Keywords": "3-4 Begriffe für Fachsuche",
              "Begruendung": "Warum passt das Bild zum Durchmesser von {mm_ist:.1f} mm?"
            }}
            """
            
            try:
                # API Aufruf mit dem neuen Client
                response = client.models.generate_content(
                    model="gemma-3-27b-it",
                    contents=[prompt, raw_img]
                )
                
                # JSON extrahieren
                text_response = response.text
                start = text_response.find('{')
                end = text_response.rfind('}') + 1
                st.session_state.analysis_result = json.loads(text_response[start:end])
                
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")
                with st.expander("Roh-Antwort der KI"):
                    st.write(response.text if 'response' in locals() else "Keine Antwort.")

# --- 3. ERGEBNIS-ANZEIGE ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🏺 Numismatischer Befund")
        st.success(f"**Bestimmung:** {res.get('Identitaet', 'Unbekannt')}")
        st.write(f"**Struktur:** {res.get('Motiv_Analyse', '-')}")
        st.write(f"**Details:** {res.get('Fein_Details', '-')}")
    with col_b:
        st.subheader("📜 Kontext & Beweise")
        st.write(f"**Legende:** `{res.get('Legende', '-')}`")
        st.info(f"**Analyse:** {res.get('Begruendung', '-')}")

    # Profi-Links
    st.subheader("🔗 Verifikation")
    search_term = f"{res.get('Identitaet', '')} {res.get('Keywords', '')} {mm_ist:.1f}mm"
    q = urllib.parse.quote(search_term)
    
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 Numista Check](https://en.numista.com/catalogue/index.php?q={q})")
    l2.markdown(f"[💰 MA-Shops Suche](https://www.ma-shops.de/result.php?searchstr={q})")
    l3.markdown(f"[🖼️ Google Bilder](https://www.google.com/search?q={q}&tbm=isch)")

    if st.button("🗑️ Neue Analyse"):
        st.session_state.analysis_result = None
        st.rerun()
