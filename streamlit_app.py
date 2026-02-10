import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import json
import urllib.parse
import io

# --- 1. SETUP & GEDÄCHTNIS ---
st.set_page_config(page_title="MuenzID Pro - Expert", layout="wide")
st.title("🪙 Münz-Detektiv: Systematische Analyse")

# Session State für Stabilität
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# Client Initialisierung (SDK v1)
# Nutze 'gemini-2.0-flash' für Grounding oder 'gemma-3-27b-it' für höhere Limits
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- 2. KALIBRIERUNG IM HAUPTBEREICH ---
st.header("📏 1. Präzisions-Messung")
st.info("Lege eine 1€ oder 2€ Münze auf das Display. Stelle den Kreis ein, bis er bündig abschließt.")

# Slider direkt unter der Info
size_px = st.slider("Kreisgröße (Pixel)", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 Kalibrieren mit 1 € (23.25 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibrierung auf 1 € gespeichert!")
with c2:
    if st.button("📍 Kalibrieren mit 2 € (25.75 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibrierung auf 2 € gespeichert!")

# Die Formel: mm = (Pixel / PPI) * 25.4
mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Gemessener Durchmesser", f"{mm_ist:.2f} mm")

# Unveränderlicher Mittelpunkt (Roter Punkt)
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 40px; background: #0e1117; border-radius: 20px; border: 1px solid #333;">
        <div style="width:{size_px}px; height:{size_px}px; border:6px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 12px; height: 12px; background: #ff4b4b; border-radius: 50%; position: absolute;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 3. FORENSISCHE BILD-ANALYSE ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # Forensik-Filter (Struktur-Fokus)
    proc = ImageOps.grayscale(raw_img)
    proc = ImageOps.autocontrast(proc, cutoff=2)
    proc = proc.filter(ImageFilter.UnsharpMask(radius=2, percent=250, threshold=3))
    
    st.image([raw_img, proc], caption=["Original", "Forensik-Filter (Relief-Fokus)"], width=400)

    if st.button("🚀 Systematische Bestimmung starten", use_container_width=True):
        with st.status("KI analysiert & verifiziert via Web-Grounding...") as status:
            
            # Der hierarchische Prompt (Vermeidet 'Schweiz'-Halluzinationen)
            prompt = f"""
            Du bist ein forensischer Numismatiker. Durchmesser: {mm_ist:.1f} mm.
            Nutze die Google Suche, um Details abzugleichen.

            HIERARCHISCHE ANALYSE:
            1. MOTIV-TYP: (Wappen, Adler, Gesicht, stehende Figur?)
            2. STRUKTUR: (Blickrichtung? Haltung? Schildteilung?)
            3. FEIN-DETAILS: (Accessoires? Bartform? Krone? Was wird gehalten - Sichel, Hammer, Zepter?)
            4. VETO-CHECK: Wenn mm > 20 und schreitende Figur -> Prüfe SÄMANN (Österreich), NICHT Helvetia (Schweiz). 
            5. OCR: Suche nach Initialen (F, I, MT) oder Werten (1, 3, 5).

            Antworte STRENG als JSON:
            {{
              "Bestimmung": "Land, Nominal, Ära",
              "Motiv": "Beschreibung von Struktur und Blickrichtung",
              "Details": "Liste aller Accessoires und Wappensymbole",
              "Legende": "Gelesene Zeichen oder [unleserlich]",
              "Analyse": "Beweisführung warum {mm_ist:.1f}mm zur Identität passt",
              "Keywords": "Fachbegriffe für die Verifikation"
            }}
            """
            
            try:
                # Nutze Search Grounding um 'Alpenhorn'-Fehler zu vermeiden
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=[prompt, proc],
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                    )
                )
                
                # JSON-Parsing (Fix für IndentationErrors)
                txt = response.text
                start, end = txt.find('{'), txt.rfind('}') + 1
                st.session_state.result = json.loads(txt[start:end])
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 4. ERGEBNIS-ANZEIGE ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**Bestimmung:** {res.get('Bestimmung', 'Unbekannt')}")
        st.write(f"**Motiv:** {res.get('Motiv', '-')}")
        st.write(f"**Details:** {res.get('Details', '-')}")
    with col_b:
        st.write(f"**Gelesene Legende:** `{res.get('Legende', '-')}`")
        st.info(f"**Beweisführung:** {res.get('Analyse', '-')}")

    # Profi-Links
    st.subheader("🔗 Verifikation & Handel")
    search_q = f"{res.get('Bestimmung', '')} {res.get('Keywords', '')} {mm_ist:.1f}mm"
    q_enc = urllib.parse.quote(search_q)
    
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 Numista Check](https://en.numista.com/catalogue/index.php?q={q_enc})")
    l2.markdown(f"[💰 MA-Shops Suche](https://www.ma-shops.de/result.php?searchstr={q_enc})")
    l3.markdown(f"[🖼️ Google Bild-Abgleich](https://www.google.com/search?q={q_enc}&tbm=isch)")

    if st.button("🗑️ Neue Analyse"):
        st.session_state.result = None
        st.rerun()
