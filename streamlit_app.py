import streamlit as st
from google import genai
from PIL import Image, ImageOps, ImageFilter
import json
import urllib.parse

# --- 1. SETUP ---
st.set_page_config(page_title="MuenzID Universal", layout="wide")
st.title("🪙 Münz-Detektiv: Universal")

# Session State
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API Client (Gemma 3 27B)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 2. OPTIONALE KALIBRIERUNG ---
st.header("1. Messung (Optional)")

# Der Umschalter für den Foto-Modus
use_diameter = st.toggle("📏 Physische Messung verwenden (Genauer)", value=True)

mm_prompt_text = "UNBEKANNT (Nur Foto-Analyse)"
mm_logic_instruction = "Bestimme den Typ rein visuell anhand von Proportionen und Schrift."

if use_diameter:
    st.info("Lege die Münze auf das Display für maximale Präzision.")
    
    col_cal1, col_cal2 = st.columns([3, 1])
    with col_cal1:
        size_px = st.slider("Kreisgröße", 100, 800, 300)
    
    with col_cal2:
        st.write("Kalibrieren:")
        c1, c2 = st.columns(2)
        if c1.button("1 €", use_container_width=True):
            st.session_state.ppi = (size_px / 23.25) * 25.4
            st.toast("1€ Kalibriert")
        if c2.button("2 €", use_container_width=True):
            st.session_state.ppi = (size_px / 25.75) * 25.4
            st.toast("2€ Kalibriert")

    # Berechnung
    mm_ist = (size_px / st.session_state.ppi) * 25.4
    st.metric("Gemessener Durchmesser", f"{mm_ist:.2f} mm")
    
    # Visueller Kreis
    st.markdown(f"""
        <div style="display: flex; justify-content: center; padding: 10px; background: #111; border-radius: 10px; margin-bottom: 20px;">
            <div style="width:{size_px}px; height:{size_px}px; border:4px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center;">
                <div style="width: 5px; height: 5px; background: red; border-radius: 50%;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Prompt-Daten setzen
    mm_prompt_text = f"{mm_ist:.1f} mm"
    mm_logic_instruction = f"Nutze den Durchmesser von {mm_ist:.1f}mm als HARTEN FILTER. Schließe Münzen aus, die deutlich größer/kleiner sind."

else:
    st.warning("⚠️ Ohne Messung kann die KI Größenverhältnisse (z.B. 10 vs 20 Kreuzer) nur schätzen.")

# --- 3. ANALYSE ---
st.header("2. Identifikation")
uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    st.image(raw_img, caption="Originalbild (Farbe)", width=400)

    if st.button("🚀 Analyse starten", use_container_width=True):
        with st.status("Analysiere Merkmale & Datenbanken...") as status:
            
            prompt = f"""
            Du bist ein professioneller Numismatiker.
            Deine Aufgabe: Bestimme die Münze basierend auf den verfügbaren Fakten.
            
            GEGEBENE FAKTEN:
            1. DURCHMESSER: {mm_prompt_text}
            
            ANALYSE-LOGIK:
            1. MATERIAL-SCAN (Farbbild):
               - Gelb -> Gold/Messing
               - Grau/Weiß -> Silber/Zink/Nickel
               - Rot/Braun -> Kupfer/Bronze
            
            2. VISUELLE ERKENNUNG:
               - Motiv (Adler, Kopf, Wappen, Figur).
               - Text/Legende (OCR).
            
            3. MATCHING-REGEL:
               - {mm_logic_instruction}
               - Falls Durchmesser UNBEKANNT: Nenne den wahrscheinlichsten Typ, aber weise auf mögliche Größenvarianten hin.

            Antworte NUR als JSON:
            {{
              "Land": "Land / Region",
              "Nominal": "Wert (z.B. 1 Dukat)",
              "Jahr_Zeitraum": "Jahr oder Epoche",
              "Material": "Erkanntes Metall",
              "Suchbegriff": "Optimierter Suchstring für Numista",
              "Begruendung": "Warum ist es diese Münze?"
            }}
            """
            
            try:
                response = client.models.generate_content(
                    model="gemma-3-27b-it", 
                    contents=[prompt, raw_img]
                )
                
                txt = response.text
                if "```json" in txt:
                    txt = txt.replace("```json", "").replace("```", "")
                
                start = txt.find('{')
                end = txt.rfind('}') + 1
                
                if start != -1 and end != -1:
                    st.session_state.result = json.loads(txt[start:end])
                    status.update(label="Gefunden!", state="complete")
                else:
                    st.error("Datenbank-Antwort unleserlich.")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 4. ERGEBNIS ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.success(f"**{res.get('Land')}**")
        st.metric("Nominal", res.get('Nominal'))
        st.info(f"Material: {res.get('Material')}")
    with c2:
        st.write(f"**Zeit:** {res.get('Jahr_Zeitraum')}")
        st.caption(f"Analyse: {res.get('Begruendung')}")
    
    # Link Generator
    s_term = res.get('Suchbegriff', f"{res.get('Land')} {res.get('Nominal')}")
    q = urllib.parse.quote(s_term)
    
    st.markdown("### 🔎 Referenzen")
    st.markdown(f"👉 [**Numista Datenbank**](https://en.numista.com/catalogue/index.php?q={q})")
    st.markdown(f"👉 [**MA-Shops Handel**](https://www.ma-shops.de/result.php?searchstr={q})")
    
    if st.button("Neu Starten"):
        st.session_state.result = None
        st.rerun()
