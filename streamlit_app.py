import streamlit as st
from google import genai
from PIL import Image, ImageOps, ImageFilter
import json
import urllib.parse

# --- SETUP ---
st.set_page_config(page_title="MuenzID - Feature Scan", layout="wide")
st.title("🪙 Münz-Detektiv: Fakten-Check")

if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API: Gemma 3 27B (Hohes Quota)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. KALIBRIERUNG (Optional, aber empfohlen) ---
st.header("1. Größen-Check (Wichtig für Filter)")
use_diameter = st.toggle("📏 Messung aktiv", value=True)

mm_text = "Unbekannt"
if use_diameter:
    size_px = st.slider("Kreisgröße", 100, 800, 300)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📍 1 € (23.25mm)", use_container_width=True):
            st.session_state.ppi = (size_px / 23.25) * 25.4
    with col2:
        if st.button("📍 2 € (25.75mm)", use_container_width=True):
            st.session_state.ppi = (size_px / 25.75) * 25.4
    
    mm_ist = (size_px / st.session_state.ppi) * 25.4
    st.metric("Durchmesser", f"{mm_ist:.2f} mm")
    mm_text = f"{mm_ist:.1f} mm"
    
    # Roter Kreis
    st.markdown(f"""
        <div style="display: flex; justify-content: center; padding: 10px; background: #222; border-radius: 10px;">
            <div style="width:{size_px}px; height:{size_px}px; border:4px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center;"></div>
        </div>
    """, unsafe_allow_html=True)

# --- 2. ANALYSE ---
st.header("2. Merkmale erkennen & Suchen")
uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Original (Farbe) für Material
    raw_img = Image.open(uploaded_file)
    st.image(raw_img, caption="Original", width=350)

    if st.button("🚀 Merkmale scannen & Bestimmen", use_container_width=True):
        with st.status("Analysiere Material & Buchstaben...") as status:
            
            prompt = f"""
            Du bist ein numismatischer Assistent.
            Durchmesser: {mm_text}.
            
            AUFGABE: Erstelle ein Profil der Münze basierend auf Fakten. Raten ist verboten.

            SCHRITT 1: MATERIAL (Schau auf das Farbbild!)
            - Gelb/Goldig -> Gold oder Messing
            - Grau/Silbrig -> Silber, Zink oder Alu
            - Rot/Braun -> Kupfer oder Bronze
            
            SCHRITT 2: SCANNE BUCHSTABEN & SYMBOLE (OCR)
            - Welche Buchstaben sind SICHTBAR? (z.B. "F", "I", "3", "S", "REPUBLIK", "SIGISMUND")
            - Welches Motiv? (Adler, Wappen, Kopf, Stehende Figur, Kreuz)
            
            SCHRITT 3: SCHLUSSFOLGERUNG
            - Kombiniere Material + Größe + Buchstaben.
            - "F" + "I" + 20mm + Silber = Ferdinand I (3 Kreuzer).
            - "S" + "1" + 25mm + Silber/Alu = Österreich Schilling.
            - "Gold" + "Stehender König" + 20mm = Ungarn Goldgulden.
            
            SCHRITT 4: SUCH-LINK GENERIERUNG
            - Erstelle Keywords für eine Google-Suche, die NICHT zu spezifisch sind.
            - Format: "Coin [Land] [Wert] [Wichtiges Merkmal]"

            Antworte NUR als JSON:
            {{
              "Material": "Erkanntes Metall",
              "Sichtbare_Zeichen": "Liste der Buchstaben/Zahlen",
              "Motiv_Beschreibung": "Was ist drauf?",
              "Bestimmungs_Versuch": "Wahrscheinlichstes Land & Nominal",
              "Such_Keywords": "3-4 Stichworte für die Suche (z.B. 'Coin Austria 1 Schilling Sower' oder 'Coin Groschen F I')",
              "Warnung": "Falls unsicher"
            }}
            """
            
            try:
                response = client.models.generate_content(
                    model="gemma-3-27b-it", 
                    contents=[prompt, raw_img]
                )
                
                txt = response.text.replace("```json", "").replace("```", "")
                res = json.loads(txt[txt.find('{'):txt.rfind('}')+1])
                st.session_state.result = res
                status.update(label="Fertig!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 3. ERGEBNIS ---
if st.session_state.result:
    r = st.session_state.result
    st.divider()
    
    # Zeige erst die FAKTEN, dann das ERGEBNIS
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Material:** {r.get('Material')}")
        st.write(f"**Zeichen:** `{r.get('Sichtbare_Zeichen')}`")
        st.write(f"**Motiv:** {r.get('Motiv_Beschreibung')}")
    with c2:
        st.success(f"**Bestimmung:** {r.get('Bestimmungs_Versuch')}")
        st.caption(f"Status: {r.get('Warnung', 'OK')}")

    # DER SICHERE LINK
    # Wir suchen nach den Keywords, nicht nach dem exakten Namen. Das bringt bessere Treffer.
    keywords = r.get('Such_Keywords', f"{r.get('Bestimmungs_Versuch')} coin")
    q = urllib.parse.quote(keywords)
    
    st.markdown("### 🔎 Eigene Prüfung starten")
    st.markdown(f"Das Ergebnis oben kann falsch sein. Prüfe diese Bilder:")
    
    col_l1, col_l2 = st.columns(2)
    # Breitere Suche bei Google Bilder (visueller Vergleich)
    col_l1.markdown(f"👉 [**Google Bilder Vergleich**](https://www.google.com/search?q={q}&tbm=isch)")
    # Spezifische Suche bei Numista
    col_l2.markdown(f"👉 [**Numista Datenbank**](https://en.numista.com/catalogue/index.php?q={q})")
    
    st.write(f"*Genutzter Suchbegriff:* `{keywords}`")
    
    if st.button("Neu"):
        st.session_state.result = None
        st.rerun()
