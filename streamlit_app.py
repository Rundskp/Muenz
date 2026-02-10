import streamlit as st
from google import genai
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import json
import urllib.parse
import io

# --- SETUP & SESSION STATE ---
st.set_page_config(page_title="MuenzID Pro - Expert", layout="wide")
st.title("🪙 Münz-Detektiv: Forensische Analyse 2026")

if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API Client (Gemma 3)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt in den Secrets!")
    st.stop()

# --- 1. KALIBRIERUNG ---
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

# Fixed-Mittelpunkt
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 30px; background: #0e1117; border-radius: 15px; border: 1px solid #333;">
        <div style="width:{size_px}px; height:{size_px}px; border:6px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 10px; height: 10px; background: #ff4b4b; border-radius: 50%; position: absolute;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. BILD-UPLOAD & ANALYSE ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # FORENSISCHER FILTER
    proc = ImageOps.grayscale(raw_img)
    proc = ImageOps.autocontrast(proc, cutoff=2)
    proc = proc.filter(ImageFilter.UnsharpMask(radius=2, percent=250, threshold=3))
    
    st.image([raw_img, proc], caption=["Original", "Forensik-Filter (Struktur-Fokus)"], width=400)

    if st.button("🚀 Systematische Bestimmung starten", use_container_width=True):
        with st.status("Analysiere Details der Details...") as status:
            prompt = f"""
            Du bist ein numismatischer Forensiker. Durchmesser: {mm_ist:.1f} mm.

            KRITISCHE PRÜFUNG (Veto-Regeln):
            1. Wenn du eine '1' und eine schreitende Figur siehst: Prüfe ZUERST ob es der ÖSTERREICHISCHE SÄMANN (Sower) ist. 
               Vergleiche den Adler: Hat er Sicheln und Hammer in den Fängen? Dann ist es ÖSTERREICH, NICHT SCHWEIZ.
            2. DIAMETER-CHECK: Ein Schweizer 1/2 Franken ist 18mm groß. Wenn der Messwert {mm_ist:.1f}mm ist, ist Schweiz extrem unwahrscheinlich!
            3. REGENLEDE: Wenn du 'REPUBLIK' liest, prüfe ob danach 'ÖSTERREICH' (stark abgenutzt) folgen könnte.

            HIERARCHISCHE ANALYSE:
            - STUFE 1: Hauptmotiv (Wappen/Adler vs. Figur).
            - STUFE 2: Details der Figur (Sämann hält Sack, Helvetia hält Schild).
            - STUFE 3: Buchstabenreste (Suche nach 'S' für Schilling oder 'REPUBLIK').

            Antworte AUSSCHLIESSLICH als JSON:
            {{
              "Bestimmung": "Land, Nominal, Jahr/Ära",
              "Details": "Genaue Beschreibung (z.B. Adler mit Bindenschild, Sämann)",
              "Legende": "Gelesene Fragmente oder [unleserlich]",
              "Analyse": "Beweisführung warum {mm_ist:.1f}mm entscheidend ist",
              "Keywords": "Fachbegriffe für Suche"
            }}
            """
            try:
                response = client.models.generate_content(
                    model="gemma-3-27b-it",
                    contents=[prompt, proc]
                )
                txt = response.text
                start, end = txt.find('{'), txt.rfind('}') + 1
                st.session_state.result = json.loads(txt[start:end])
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 3. ERGEBNIS-ANZEIGE ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**Bestimmung:** {res.get('Bestimmung', 'Unbekannt')}")
        st.write(f"**Details:** {res.get('Details', '-')}")
    with col_b:
        st.write(f"**Gelesene Legende:** `{res.get('Legende', '-')}`")
        st.info(f"**Forensische Analyse:** {res.get('Analyse', '-')}")

    # Profi-Links
    st.subheader("🔗 Verifikation")
    search_q = f"{res.get('Bestimmung', '')} {res.get('Keywords', '')} {mm_ist:.1f}mm"
    q_enc = urllib.parse.quote(search_q)
    
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 Numista Datenbank](https://en.numista.com/catalogue/index.php?q={q_enc})")
    l2.markdown(f"[💰 MA-Shops Handel](https://www.ma-shops.de/result.php?searchstr={q_enc})")
    l3.markdown(f"[🖼️ Google Bild-Abgleich](https://www.google.com/search?q={q_enc}&tbm=isch)")

    if st.button("🗑️ Neue Analyse"):
        st.session_state.result = None
        st.rerun()
