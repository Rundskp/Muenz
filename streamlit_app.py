import streamlit as st
from google import genai
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import json
import urllib.parse
import io

# --- SETUP & SESSION STATE ---
st.set_page_config(page_title="MuenzID Pro - Expert", layout="wide")
st.title("🪙 Münz-Detektiv: Forensische Analyse (Fix)")

if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# Client Initialisierung (Gemma 3 27B)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. KALIBRIERUNG ---
st.header("📏 1. Physische Kalibrierung")
size_px = st.slider("Kreisgröße (Pixel)", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 Kalibrieren 1 €", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
with c2:
    if st.button("📍 Kalibrieren 2 €", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Gemessener Durchmesser", f"{mm_ist:.2f} mm")

# --- 2. BILD-UPLOAD & ANALYSE ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # EXTREMER FORENSIK-FILTER
    proc = ImageOps.grayscale(raw_img)
    proc = ImageOps.autocontrast(proc, cutoff=2)
    proc = proc.filter(ImageFilter.UnsharpMask(radius=3, percent=300, threshold=2))
    
    st.image([raw_img, proc], caption=["Original", "Forensik-Filter (Fokus auf Zeichen)"], width=400)

    if st.button("🚀 Systematische Bestimmung starten"):
        with st.status("Hierarchische Tiefenprüfung...") as status:
            prompt = f"""
            Du bist ein forensischer Numismatiker. Durchmesser: {mm_ist:.1f} mm.

            STRENGSTE ANWEISUNG:
            1. INITIALEN-PRIORITÄT: Wenn große Buchstaben wie 'F', 'I', 'M' oder 'T' sichtbar sind, haben diese Vorrang vor Motiven wie dem 'Sämann'.
            2. PRÜFUNG: Suche nach einem Dreipass (Trilobe) mit Buchstaben in den Bögen. 
            3. VERBOT: Identifiziere eine Münze mit 'F' und 'I' NIEMALS als modernen Schilling. Das ist Ferdinand I. (Habsburg).

            HIERARCHIE:
            - STUFE 1: Große Buchstaben/Zahlen (OCR).
            - STUFE 2: Rahmenformen (Dreipass, Kreis, Wappen).
            - STUFE 3: Synthese mit Durchmesser {mm_ist:.1f}mm.

            Antworte NUR als JSON:
            {{
              "Bestimmung": "Land, Nominal, Herrscher",
              "Details": "Beschreibung der Zeichen (z.B. F und I im Dreipass)",
              "Analyse": "Beweisführung warum es KEIN Schilling ist",
              "Link_Keywords": "Suchbegriffe für Profi-Suche"
            }}
            """
            try:
                response = client.models.generate_content(
                    model="gemma-3-27b-it",
                    contents=[prompt, proc]
                )
                # JSON-Bereinigung & Parsing
                raw_txt = response.text.strip()
                start = raw_txt.find('{')
                end = raw_txt.rfind('}') + 1
                st.session_state.result = json.loads(raw_txt[start:end])
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"API Fehler: {e}")

# --- 3. ERGEBNIS-ANZEIGE ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    st.success(f"**Bestimmung:** {res.get('Bestimmung', 'Unbekannt')}")
    st.write(f"**Details:** {res.get('Details', '-')}")
    st.info(f"**Analyse:** {res.get('Analyse', '-')}")

    # Profi-Links
    q = urllib.parse.quote(f"{res.get('Bestimmung', '')} {res.get('Link_Keywords', '')} {mm_ist:.1f}mm")
    st.markdown(f"### 🔗 [Prüfen auf Numista](https://en.numista.com/catalogue/index.php?q={q})")
