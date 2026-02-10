import streamlit as st
from google import genai
from google.genai import types # Für das Search-Tool
from PIL import Image, ImageOps, ImageFilter
import json
import urllib.parse

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Lens Edition", layout="wide")
st.title("🪙 Münz-Detektiv: KI + Google Search Filter")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# Client mit Such-Tool Initialisierung
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 1. KALIBRIERUNG (Unverändert) ---
st.header("📏 1. Präzisions-Messung")
size_px = st.slider("Kreisgröße", 100, 800, 300)
# (Hier bleibt deine bewährte 1€/2€ Kalibrierungs-Logik stehen)

# --- 2. INTELLIGENTE ANALYSE ---
st.header("🔍 2. Bild-Analyse mit Live-Web-Abgleich")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # Forensik-Filter (Schärfung der Kanten für die Suche)
    proc = ImageOps.grayscale(raw_img)
    proc = proc.filter(ImageFilter.UnsharpMask(radius=3, percent=250, threshold=2))
    
    st.image([raw_img, proc], caption=["Original", "Forensik-Filter (Struktur-Fokus)"], width=400)

    if st.button("🚀 Suche & Filterung starten"):
        with st.status("KI nutzt Google Search zur Verifizierung...") as status:
            
            prompt = f"""
            Analysiere diese Münze. Durchmesser: {mm_ist:.1f} mm.
            
            DEIN ARBEITSABLAUF (LENS-LOGIK):
            1. NUTZE GOOGLE SEARCH: Suche nach Münzen mit diesen Merkmalen (z.B. schreitende Figur, Adler mit Sicheln, Initialen F-I).
            2. FILTERN: Vergleiche die Web-Ergebnisse mit dem vorliegenden Bild. 
               - Wenn 19.8mm und 'F-I' -> Wahrscheinlich Ferdinand I.
               - Wenn 25mm und Sämann -> Österreich 1 Schilling.
            3. KONTROLLE: Schließe Verwechslungen mit der Schweiz (Helvetia) aktiv aus, falls der Durchmesser nicht passt.

            Antworte NUR als JSON:
            {{
              "Bestimmung": "Exakte Identität",
              "Web_Vergleich": "Welche Treffer hast du bei Google gefunden?",
              "Details": "Visuelle Merkmale im Bild",
              "Vertrauen": "0-100%",
              "Link": "Bester Numista- oder Handels-Link"
            }}
            """
            
            try:
                # Aufruf mit Google Search Grounding Tool
                response = client.models.generate_content(
                    model="gemini-2.0-flash", # Oder gemma-3-27b-it
                    contents=[prompt, proc],
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                    )
                )
                
                txt = response.text
                start, end = txt.find('{'), txt.rfind('}') + 1
                st.session_state.analysis_result = json.loads(txt[start:end])
                status.update(label="Analyse & Web-Abgleich abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 3. ANZEIGE ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    st.divider()
    st.success(f"**Ergebnis:** {res['Bestimmung']} (Vertrauen: {res['Vertrauen']})")
    st.write(f"**Web-Check:** {res['Web_Vergleich']}")
    st.info(f"**Details:** {res['Details']}")
    st.markdown(f"### 🔗 [Direkt zum Referenz-Stück]({res['Link']})")
