import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import json
import urllib.parse
import io

# --- 1. GRUND-SETUP ---
st.set_page_config(page_title="MuenzID Pro - Ultra", layout="wide")
st.title("🪙 Münz-Detektiv: Forensik & Web-Grounding")

# Gedächtnis (Session State) für Stabilität
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API Client Initialisierung (SDK v1)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt in den Streamlit Secrets!")
    st.stop()

# --- 2. KALIBRIERUNG (Zentrum der App) ---
st.header("📏 1. Physische Kalibrierung")
st.info("Lege eine 1€ oder 2€ Münze auf das Display. Stelle den Kreis ein, bis er bündig abschließt.")

size_px = st.slider("Kreisgröße (Pixel)", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 Kalibrieren mit 1 € (23.25 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibriert auf 1 €")
with c2:
    if st.button("📍 Kalibrieren mit 2 € (25.75 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibriert auf 2 €")

# Durchmesser-Berechnung: $mm = \frac{size\_px}{ppi} \cdot 25.4$
mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Gemessener Durchmesser", f"{mm_ist:.2f} mm")

# Fixed-Center Messkreis (UI Anker)
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 40px; background: #0e1117; border-radius: 20px; border: 1px solid #333;">
        <div style="width:{size_px}px; height:{size_px}px; border:6px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 12px; height: 12px; background: #ff4b4b; border-radius: 50%; position: absolute;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 3. BILD-ANALYSE ---
st.header("🔍 2. Forensische Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # --- FORENSIK-FILTER (Struktur-Extraktion) ---
    proc = ImageOps.grayscale(raw_img) # Graustufen
    proc = ImageOps.autocontrast(proc, cutoff=2) # Histogramm-Spreizung
    proc = proc.filter(ImageFilter.UnsharpMask(radius=2, percent=250, threshold=3)) # Kanten-Relief
    
    st.image([raw_img, proc], caption=["Originalbild", "Forensik-Filter (Struktur-Fokus)"], width=400)

    if st.button("🚀 Systematische Bestimmung starten", use_container_width=True):
        with st.status("KI analysiert & verifiziert via Google Search...") as status:
            
            # Hierarchischer Prompt mit Veto-Regeln
            prompt = f"""
            Du bist ein forensischer Numismatiker. Durchmesser: {mm_ist:.1f} mm.
            Nutze Google Search, um deine Vermutungen zu verifizieren.

            ANALYSE-HIERARCHIE:
            1. MOTIV: Was ist das Hauptmotiv? (Bsp: Schreitende Figur, Wappen, Kopf).
            2. STRUKTUR-VETO: Wenn Durchmesser > 20mm und Figur sichtbar -> Prüfe ÖSTERREICH SÄMANN (1 Schilling), NICHT Schweiz (1/2 Franken).
            3. DETAILS DER DETAILS: Was hält die Figur (Sichel, Hammer, Zepter)? Was ist im Wappen (Löwen, Adler)? Gibt es Initialen (F, I, MT)?
            4. LEGENDE: Lies Fragmente. Wenn unleserlich, nutze [unleserlich].

            Antworte STRENG als JSON:
            {{
              "Bestimmung": "Land, Nominal, Ära",
              "Web_Check": "Ergebnis des Abgleichs mit Google Search",
              "Details": "Struktur & Fein-Merkmale (Bart, Krone, Accessoires)",
              "Legende": "Gelesene Zeichen",
              "Analyse": "Beweisführung warum {mm_ist:.1f}mm zur Identität passt",
              "Keywords": "Suchbegriffe für die Verifikation"
            }}
            """
            
            try:
                # API Aufruf mit Search Grounding Tool
                response = client.models.generate_content(
                    model="gemini-2.0-flash", # Bestes Modell für Search Grounding
                    contents=[prompt, proc],
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                    )
                )
                
                txt = response.text
                start, end = txt.find('{'), txt.rfind('}') + 1
                st.session_state.result = json.loads(txt[start:end])
                status.update(label="Analyse & Verifikation abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 4. ERGEBNIS-ANZEIGE (Persistiert im Session State) ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**Bestimmung:** {res.get('Bestimmung', 'Unbekannt')}")
        st.write(f"**Web-Check:** {res.get('Web_Check', '-')}")
        st.write(f"**Fein-Details:** {res.get('Details', '-')}")
    with col_b:
        st.write(f"**Legende:** `{res.get('Legende', '-')}`")
        st.info(f"**Beweisführung:** {res.get('Analyse', '-')}")

    # Profi-Links
    st.subheader("🔗 Verifikation & Handel")
    search_q = f"{res.get('Bestimmung', '')} {res.get('Keywords', '')} {mm_ist:.1f}mm"
    q_enc = urllib.parse.quote(search_q)
    
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 Numista Check](https://en.numista.com/catalogue/index.php?q={q_enc})")
    l2.markdown(f"[💰 MA-Shops Suche](https://www.ma-shops.de/result.php?searchstr={q_enc})")
    l3.markdown(f"[🖼️ Google Bilder](https://www.google.com/search?q={q_enc}&tbm=isch)")
    
    if st.button("🗑️ Neue Analyse starten"):
        st.session_state.result = None
        st.rerun()
