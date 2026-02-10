import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import json
import urllib.parse
import io

# --- 1. SETUP ---
st.set_page_config(page_title="MuenzID Pro", layout="wide")
st.title("🪙 Münz-Detektiv: Experten-Version")

# Gedächtnis (Session State) - KRITISCH FÜR DIE ANZEIGE
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API Client (Wechsel auf Gemma 3 27B wegen 15k Limit)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 2. KALIBRIERUNG ---
st.header("📏 1. Kalibrierung")
size_px = st.slider("Kreisgröße anpassen", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 1 € (23.25mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
with c2:
    if st.button("📍 2 € (25.75mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Messwert", f"{mm_ist:.2f} mm")

# Fixed Mittelpunkt Kreis
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 20px; background: #0e1117; border-radius: 10px;">
        <div style="width:{size_px}px; height:{size_px}px; border:5px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center;">
            <div style="width: 8px; height: 8px; background: red; border-radius: 50%;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 3. ANALYSE-LOGIK ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    
    # Forensik-Filter
    proc = ImageOps.grayscale(img)
    proc = proc.filter(ImageFilter.UnsharpMask(radius=2, percent=250, threshold=3))
    
    st.image([img, proc], caption=["Original", "Forensik-Filter"], width=300)

    if st.button("🚀 Analyse starten", use_container_width=True):
        with st.status("KI arbeitet...") as status:
            prompt = f"""
            Analysiere diese Münze. Durchmesser: {mm_ist:.1f} mm.
            - Prüfe Motiv (Wappen, Adler, Figur).
            - Suche nach Buchstaben (F-I, S, REPUBLIK).
            - VETO: Wenn mm > 20 und Figur -> Österreich 1 Schilling, NICHT Schweiz.
            Antworte NUR als JSON:
            {{ "Bestimmung": "Land, Wert", "Details": "Merkmale", "Legende": "Text", "Analyse": "Beweis" }}
            """
            try:
                # Wir nutzen Gemma 3 27B für stabiles Quota
                response = client.models.generate_content(
                    model="gemma-3-27b-it", 
                    contents=[prompt, proc]
                )
                txt = response.text
                # JSON sicher extrahieren
                res_data = json.loads(txt[txt.find('{'):txt.rfind('}')+1])
                # WICHTIG: Im Session State speichern
                st.session_state.result = res_data
                status.update(label="Fertig!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 4. ANZEIGE (AUSSERHALB DES BUTTONS) ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    st.success(f"**Ergebnis:** {res.get('Bestimmung')}")
    st.write(f"**Beweis:** {res.get('Analyse')}")
    
    # Such-Links
    q = urllib.parse.quote(f"{res.get('Bestimmung')} {mm_ist:.1f}mm")
    st.markdown(f"### 🔗 [Auf Numista prüfen](https://en.numista.com/catalogue/index.php?q={q})")
    
    if st.button("🗑️ Zurücksetzen"):
        st.session_state.result = None
        st.rerun()
