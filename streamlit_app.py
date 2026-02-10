import streamlit as st
from google import genai
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import json
import urllib.parse
import io

# --- SETUP & SESSION STATE ---
st.set_page_config(page_title="MuenzID Pro - Expert", layout="wide")
st.title("🪙 Münz-Detektiv: Forensische Analyse")

# Initialisierung des Gedächtnisses
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API Client Initialisierung (Gemma 3)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- 1. KALIBRIERUNG & MESSUNG ---
st.header("📏 1. Physische Kalibrierung")
st.info("Lege eine 1€ oder 2€ Münze auf das Display und stelle den Kreis passgenau ein.")

size_px = st.slider("Kreisgröße (Pixel)", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 Kalibrieren 1 € (23.25 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibrierung auf 1 € gespeichert!")
with c2:
    if st.button("📍 Kalibrieren 2 € (25.75 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibrierung auf 2 € gespeichert!")

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Gemessener Durchmesser", f"{mm_ist:.2f} mm")

# Unveränderlicher Mittelpunkt für die physische Münze
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 30px; background: #0e1117; border-radius: 15px; border: 1px solid #333;">
        <div style="width:{size_px}px; height:{size_px}px; border:6px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 10px; height: 10px; background: #ff4b4b; border-radius: 50%; position: absolute;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. HIERARCHISCHE ANALYSE ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen (Bodenfunde/Abgenutzt erlaubt)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # --- FORENSISCHE BILD-OPTIMIERUNG ---
    # 1. Graustufen zur Rauschreduzierung
    proc = ImageOps.grayscale(raw_img)
    # 2. Autocontrast zur Spreizung des Histogramms
    proc = ImageOps.autocontrast(proc, cutoff=2)
    # 3. Aggressive Kanten-Schärfung (Unsharp Mask) für OCR-Verbesserung
    proc = proc.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=3))
    
    st.image([raw_img, proc], caption=["Originalbild", "Forensik-Filter (Struktur-Fokus)"], width=400)

    if st.button("🚀 Systematische Bestimmung starten", use_container_width=True):
        with st.status("Analysiere Details der Details...") as status:
            prompt = f"""
            Analysiere diese Münze streng hierarchisch. Durchmesser: {mm_ist:.1f} mm.

            REGEL: Sei ehrlich. Wenn Legenden unleserlich sind, schreibe [unleserlich]. Erfinde nichts!

            STUFE 1: MOTIV-IDENTIFIKATION
            Bestimme das Hauptmotiv (z.B. Wappen, Adler, Kopf, stehende Figur/Sämann). 

            STUFE 2: STRUKTUR-ANALYSE
            - Wappen: Teilung (geviertelt?), Wappeninhalte exakt prüfen (z.B. Löwen, Balken).
            - Kopf/Figur: Blickrichtung? Haltung? (Bsp: Schreitender Mann, der Saatgut verstreut).

            STUFE 3: FEIN-DETAILS
            - Accessoires: Was wird gehalten (Zepter, Reichsapfel, Kind, Sichel, Hammer)?
            - Merkmale: Bart, Brille, Haarlänge, Krone?
            - Such-Fokus: Suche bei Zahlen wie '1' explizit nach Begleitbuchstaben (S, G, K).

            STUFE 4: LEGENDE & KONTEXT
            Transkribiere Buchstaben rundherum. Verknüpfe gelesene Fragmente mit dem Motiv.

            Antworte AUSSCHLIESSLICH im JSON-Format:
            {{
              "Bestimmung": "Land, Nominal, Jahr/Herrscher",
              "Struktur_Details": "Beschreibung des Motivs und der Haltung",
              "Feinheiten": "Liste aller Accessoires und Wappensymbole",
              "Legende": "Gelesene Fragmente oder [unleserlich]",
              "Handels_Keywords": "Numismatische Fachbegriffe für Profi-Suche",
              "Analyse": "Beweisführung basierend auf Durchmesser {mm_ist:.1f}mm"
            }}
            """
            try:
                # Sende das optimierte Forensik-Bild
                response = client.models.generate_content(
                    model="gemma-3-27b-it",
                    contents=[prompt, proc]
                )
                
                # JSON-Parsing (Fix für Indentation/Extra-Text)
                txt = response.text
                start = txt.find('{')
                end = txt.rfind('}') + 1
                st.session_state.result = json.loads(txt[start:end])
                
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler bei der API-Analyse: {e}")

# --- 3. ERGEBNIS-ANZEIGE ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**Bestimmung:** {res.get('Bestimmung', 'Unbekannt')}")
        st.write(f"**Motiv-Struktur:** {res.get('Struktur_Details', '-')}")
        st.write(f"**Feinheiten:** {res.get('Feinheiten', '-')}")
    with col_b:
        st.write(f"**Gelesene Legende:** `{res.get('Legende', '-')}`")
        st.info(f"**Forensische Analyse:** {res.get('Analyse', '-')}")

    # Profi-Links
    st.subheader("🔗 Verifikation & Handel")
    search_q = f"{res.get('Bestimmung', '')} {res.get('Handels_Keywords', '')} {mm_ist:.1f}mm"
    q_enc = urllib.parse.quote(search_q)
    
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 Numista Datenbank](https://en.numista.com/catalogue/index.php?q={q_enc})")
    l2.markdown(f"[💰 MA-Shops Handel](https://www.ma-shops.de/result.php?searchstr={q_enc})")
    l3.markdown(f"[🖼️ Google Bild-Abgleich](https://www.google.com/search?q={q_enc}&tbm=isch)")

    if st.button("🗑️ Neue Analyse"):
        st.session_state.result = None
        st.rerun()
