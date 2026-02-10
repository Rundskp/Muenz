import streamlit as st
from google import genai
from PIL import Image, ImageOps, ImageFilter
import json
import urllib.parse

# --- 1. SETUP ---
st.set_page_config(page_title="MuenzID Pro - Match Finder", layout="wide")
st.title("🪙 Münz-Detektiv: Fakten & Datenbank-Match")

# Session State
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API Client (Gemma 3 27B - Stabil & Klug)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- 2. PRÄZISIONS-MESSUNG ---
st.header("📏 1. Kalibrierung (Der wichtigste Filter)")
st.info("Lege eine 1€ oder 2€ Münze auf das Display. Stelle den Kreis ein.")

size_px = st.slider("Kreisgröße", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 1 € (23.25mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibriert auf 1€")
with c2:
    if st.button("📍 2 € (25.75mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibriert auf 2€")

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Messwert", f"{mm_ist:.2f} mm")

# Fixed Circle
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 20px; background: #111; border-radius: 10px;">
        <div style="width:{size_px}px; height:{size_px}px; border:4px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center;">
            <div style="width: 5px; height: 5px; background: red; border-radius: 50%;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 3. ANALYSE-LOGIK ---
st.header("🔍 2. Identifikation")
uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    
    # Forensik-Filter (Nur zur besseren Lesbarkeit für die KI)
    proc = ImageOps.grayscale(img)
    proc = proc.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    st.image([img, proc], caption=["Original", "Struktur-Scan"], width=400)

    if st.button("🚀 Match in Datenbank suchen", use_container_width=True):
        with st.status("Extrahiere Merkmale & suche Übereinstimmungen...") as status:
            
            # Der Prompt, der das Ziel fokussiert
            prompt = f"""
            Du bist ein numismatischer Experte. Deine Aufgabe ist es, eine Münze anhand visueller Fakten in deiner internen Datenbank zu finden.
            
            GEGEBENE FAKTEN:
            - Durchmesser (gemessen): {mm_ist:.1f} mm (+/- 0.5mm Toleranz)
            
            DEIN PROZESS (SCHRITT FÜR SCHRITT):
            1. SCANNE VORDERSEITE & RÜCKSEITE:
               - Was ist das Hauptmotiv? (Stehende Figur, Kopf, Wappen, Adler, Zahl?)
               - Welche Buchstaben/Zahlen sind erkennbar? (OCR)
            
            2. DATENBANK-ABGLEICH (MATCHING):
               - Suche nach Münzen, die ALLE diese Kriterien erfüllen:
                 a) Durchmesser passt zu {mm_ist:.1f}mm
                 b) Motiv passt (z.B. Heiliger Ladislaus vs. Sämann vs. Ferdinand)
                 c) Textfragmente passen.
            
            3. ERGEBNIS-PROFIL:
               - Bestimme Land, Herrscher, Jahr/Zeitraum.
               - Bestimme das Material (Gold, Silber, Bronze, Alu) anhand des Aussehens und Typs.
               - Schätze den Wert (grob: Materialwert oder Sammlerwert).

            Antworte NUR als JSON:
            {{
              "Land": "Land / Region",
              "Zeitraum": "Prägezeitraum oder Jahr",
              "Nominal": "Währungswert",
              "Herrscher": "Name des Herrschers oder Republik",
              "Material": "Vermutetes Metall",
              "Wert_Schaetzung": "Ca. Wert (in Euro)",
              "Erkannte_Merkmale": "Liste der Übereinstimmungen (Motiv, Text, Größe)",
              "Sicherheit": "Hoch/Mittel/Niedrig"
            }}
            """
            
            try:
                # API Call
                response = client.models.generate_content(
                    model="gemma-3-27b-it", 
                    contents=[prompt, proc]
                )
                
                # Sauberes Parsing
                txt = response.text
                if "```json" in txt:
                    txt = txt.replace("```json", "").replace("```", "")
                start = txt.find('{')
                end = txt.rfind('}') + 1
                
                if start != -1 and end != -1:
                    st.session_state.result = json.loads(txt[start:end])
                    status.update(label="Treffer gefunden!", state="complete")
                else:
                    st.error("Datenbank-Antwort war unleserlich.")
                    
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 4. ERGEBNIS-DARSTELLUNG ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    # Die ZIEL-INFORMATIONEN auf einen Blick
    c1, c2, c3 = st.columns(3)
    c1.metric("Land & Herrscher", f"{res.get('Land')}\n{res.get('Herrscher')}")
    c2.metric("Nominal & Jahr", f"{res.get('Nominal')}\n{res.get('Zeitraum')}")
    c3.metric("Material & Wert", f"{res.get('Material')}\n{res.get('Wert_Schaetzung')}")
    
    st.success(f"**Übereinstimmungs-Analyse:** {res.get('Erkannte_Merkmale')}")
    st.caption(f"Sicherheit der Bestimmung: {res.get('Sicherheit')}")
    
    # Such-Links für den Beweis
    search_q = f"{res.get('Land')} {res.get('Herrscher')} {res.get('Nominal')} {res.get('Zeitraum')}"
    q = urllib.parse.quote(search_q)
    st.markdown(f"### 🔎 [Beweis auf Numista ansehen](https://en.numista.com/catalogue/index.php?q={q})")
    
    if st.button("Neue Suche"):
        st.session_state.result = None
        st.rerun()
