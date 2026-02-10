import streamlit as st
from google import genai
from PIL import Image, ImageEnhance
import json
import urllib.parse
import io

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Systematik", layout="wide")
st.title("🪙 Münz-Detektiv: Hierarchische Systematik")

# Gedächtnis der App (Session State)
if "ppi" not in st.session_state:
    st.session_state.ppi = 160.0
if "result" not in st.session_state:
    st.session_state.result = None

# API Client (SDK v1 für Gemma 3)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. KALIBRIERUNG (Zentrum) ---
st.header("📏 1. Kalibrierung & Messung")
st.info("Lege eine 1€ oder 2€ Münze auf das Display. Stelle den Regler ein, bis der goldene Kreis die Münze umschließt.")

# Slider im Hauptbereich
size_px = st.slider("Kreisgröße anpassen", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 Kalibrieren mit 1 € (23.25 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.toast("Kalibriert auf 1 €!")
with c2:
    if st.button("📍 Kalibrieren mit 2 € (25.75 mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.toast("Kalibriert auf 2 €!")

mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Messwert", f"{mm_ist:.2f} mm")

# Fixed-Center Messkreis
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 40px; background: #0e1117; border-radius: 20px; border: 1px solid #333;">
        <div style="width:{size_px}px; height:{size_px}px; border:6px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 12px; height: 12px; background: #ff4b4b; border-radius: 50%; position: absolute;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. HIERARCHISCHE ANALYSE ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    st.image(raw_img, caption="Prüfobjekt", width=400)

    if st.button("🚀 Systematische Bestimmung starten", use_container_width=True):
        with st.status("Analysiere Details der Details...") as status:
            prompt = f"""
            Analysiere diese Münze streng hierarchisch. Durchmesser: {mm_ist:.1f} mm.

            STUFE 1: MOTIV (Was liegt vor?)
            Identifiziere: Wappen, Adler, Gesicht/Kopf, Figur (stehend/sitzend), oder Zahl?

            STUFE 2: STRUKTUR (Wie ist es aufgebaut?)
            - Wappen: Schildform? Geteilt, geviertelt? Blickrichtung von Tieren?
            - Gesicht: Profil/frontal? Blickrichtung? 
            - Figur: Haltung, Kleidung?

            STUFE 3: DETAIL DER DETAILS (Tiefenprüfung)
            - Wappen-Inhalt: Exakte Symbole in JEDEM Teil. Zähle Elemente (z.B. 3 Balken, 2 Löwen).
            - Accessoires: Krone (Typ?), Zepter, Reichsapfel, Waage, Kind, Schwert, Augenbinde?
            - Physiognomie: Bart (Typ?), Brille, Haarlänge, markante Merkmale?

            STUFE 4: KONTEXT (Text & Zahlen)
            - Buchstaben: Was steht rundherum? Was steht im Abschnitt oder in der Mitte?
            - Bringe gelesene Zeichen in direkten Kontext zu den Details aus Stufe 3.

            Antworte AUSSCHLIESSLICH im JSON-Format:
            {{
              "Bestimmung": "Land, Nominal, Herrscher/Republik",
              "Motiv": "Haupttyp und Blickrichtungen",
              "Fein_Details": "Umfassende Liste aller Accessoires, Bartelemente und Wappeninhalte",
              "Legende": "Gelesene Zeichen und Bedeutung",
              "Handels_Keywords": "Präzise numismatische Suchbegriffe",
              "Analyse": "Warum passt das zu {mm_ist:.1f} mm?"
            }}
            """
            try:
                # Bildverbesserung (Silent)
                enhanced = ImageEnhance.Contrast(raw_img).enhance(1.8)
                response = client.models.generate_content(
                    model="gemma-3-27b-it",
                    contents=[prompt, enhanced]
                )
                
                # Robustes JSON-Parsing
                txt = response.text
                start, end = txt.find('{'), txt.rfind('}') + 1
                st.session_state.result = json.loads(txt[start:end])
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.write(response.text if 'response' in locals() else "Keine API-Antwort.")

# --- 3. ERGEBNIS-ANZEIGE ---
# Dieser Teil liegt AUSSERHALB des Buttons und bleibt daher stehen!
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**Bestimmung:** {res['Bestimmung']}")
        st.write(f"**Struktur & Motiv:** {res['Motiv']}")
        st.write(f"**Details der Details:** {res['Fein_Details']}")
    with col_b:
        st.write(f"**Legende (Kontext):** `{res['Legende']}`")
        st.info(f"**Beweisführung:** {res['Analyse']}")

    # Profi-Links
    st.subheader("🔗 Verifikation")
    search_q = f"{res['Bestimmung']} {res['Handels_Keywords']} {mm_ist:.1f}mm"
    q_enc = urllib.parse.quote(search_q)
    
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 Numista Check](https://en.numista.com/catalogue/index.php?q={q_enc})")
    l2.markdown(f"[💰 MA-Shops Suche](https://www.ma-shops.de/result.php?searchstr={q_enc})")
    l3.markdown(f"[🖼️ Google Bilder](https://www.google.com/search?q={q_enc}&tbm=isch)")
    
    if st.button("🗑️ Neue Analyse starten"):
        st.session_state.result = None
        st.rerun()
