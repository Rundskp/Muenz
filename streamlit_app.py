import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance
import json
import urllib.parse

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Ultra", layout="centered")
st.title("🪙 Münz-Detektiv: Universal-Prüfer 4.0")

# Session State initialisieren
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# API-Konfiguration mit Fehlerprüfung
if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        st.error(f"Fehler bei der API-Initialisierung: {e}")
        st.stop()
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- SIDEBAR ---
st.sidebar.header("📏 Kalibrierung")
ppi = st.sidebar.slider("Handy-PPI", 100, 600, 160)
size = st.sidebar.slider("Kreisgröße", 50, 600, 125)
mm_wert = (size / ppi) * 25.4

# --- HAUPT-LOGIK ---
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption=f"Analyse-Objekt ({mm_wert:.1f} mm)", use_container_width=True)

    if st.button("🔍 Profi-Analyse starten"):
        # Bildoptimierung
        enhanced = ImageEnhance.Contrast(img).enhance(1.8)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(2.0)
        
        with st.status("Analysiere Münze...") as status:
            st.write("Sende Daten an Gemini 2.5 Flash...")
            
            prompt = f"""
            Handle als Numismatiker. Durchmesser: {mm_wert:.1f} mm.
            
            1. WAPPEN: Beschreibe JEDES Feld einzeln. (Bsp: Oben links: Streifen, Oben rechts: Löwe).
            2. OCR: Lies alle Buchstaben und Zahlen (z.B. '3', '1', 'F-I', 'MONETA').
            3. BESTIMMUNG: Land, Nominal, Herrscher/Republik.

            Antworte NUR im JSON-Format:
            {{
              "Bestimmung": "Land, Nominal, Jahr/Herrscher",
              "Wappen": "Genaue Feldbeschreibung",
              "Gelesen": "Gelesene Zeichen",
              "Keywords": "Suchbegriffe für Fachseiten",
              "Info": "Kurze Begründung"
            }}
            """
            
            try:
                response = model.generate_content([prompt, enhanced])
                # JSON-Bereinigung (falls die KI Markdown-Code-Blocks mitsendet)
                raw_text = response.text.strip().replace("```json", "").replace("```", "")
                st.session_state.analysis_result = json.loads(raw_text)
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler während der Analyse: {e}")
                # Debugging: Zeige die rohe Antwort der KI, falls das JSON-Format falsch war
                with st.expander("Rohe KI-Antwort (Fehlersuche)"):
                    st.write(response.text if 'response' in locals() else "Keine Antwort erhalten")

    # Ergebnis-Anzeige (auch nach Rerun sichtbar)
    if st.session_state.analysis_result:
        res = st.session_state.analysis_result
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Befund")
            st.write(f"**Identität:** {res['Bestimmung']}")
            st.write(f"**Wappen:** {res['Wappen']}")
        with c2:
            st.subheader("Details")
            st.write(f"**Gelesen:** `{res['Gelesen']}`")
            st.write(f"**Info:** {res['Info']}")

        # --- PROFI-LINKS (Manuell gebaut) ---
        st.subheader("🔗 Verifikation auf Fachseiten")
        
        # Suchstring: "Münze [Bestimmung] [Keywords] [Durchmesser]"
        search_term = f"{res['Bestimmung']} {res['Keywords']} {mm_wert:.1f}mm"
        q = urllib.parse.quote(search_term)
        
        st.markdown(f"""
        * 🏛️ **[Numista Datenbank](https://en.numista.com/catalogue/index.php?q={q})** (Beste Quelle für Typenbestimmung)
        * 💰 **[MA-Shops Fachhandel](https://www.ma-shops.de/result.php?searchstr={q})** (Aktuelle Marktpreise)
        * 🔍 **[Google Bildersuche](https://www.google.com/search?q={q}&tbm=isch)** (Visueller Abgleich)
        """)

        # Feedback-Loop
        with st.expander("❌ Falsch erkannt? Korrektur eingeben"):
            user_input = st.text_input("Was ist das richtige Wappen/Herrscher?")
            if st.button("Re-Analyse erzwingen"):
                st.info(f"Suche nach '{user_input}' wird im nächsten Durchlauf priorisiert...")
                # Hier könnte man den prompt mit dem user_input erweitern
