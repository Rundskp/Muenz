import streamlit as st
from google import genai
from PIL import Image, ImageEnhance
import json
import urllib.parse
import io

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro 2026", layout="wide")
st.title("🪙 Münz-Detektiv: Hierarchische Analyse")

# Session State für stabiles Gedächtnis
if "ppi" not in st.session_state:
    st.session_state.ppi = 160
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# Client Initialisierung (SDK v1)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. KALIBRIERUNG (Zentral) ---
st.header("📏 1. Kalibrierung mit Referenz")
st.write("Lege eine 1€ oder 2€ Münze auf das Display. Schiebe den Regler, bis der Kreis sie umschließt.")

# Der Schieberegler direkt im Hauptbereich
size_px = st.slider("Kreisgröße (Pixel)", 100, 800, 300)

c1, c2 = st.columns(2)
with c1:
    if st.button("📍 Kalibrieren auf 1 € (23.25mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.success("Kalibriert auf 1 €")
with c2:
    if st.button("📍 Kalibrieren auf 2 € (25.75mm)", use_container_width=True):
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.success("Kalibriert auf 2 €")

# Durchmesser-Berechnung
mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Gemessener Durchmesser", f"{mm_ist:.2f} mm")

# Der fixierte Messkreis mit Mittelpunkt
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 30px; background: #121212; border-radius: 10px; margin-bottom: 20px;">
        <div style="width:{size_px}px; height:{size_px}px; border:5px solid #FFD700; border-radius:50%; display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 10px; height: 10px; background: #FF4B4B; border-radius: 50%; position: absolute;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. HIERARCHISCHE ANALYSE ---
st.header("🔍 2. Detail-Analyse")
uploaded_file = st.file_uploader("Münzbild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Prüfobjekt", width=400)

    if st.button("🚀 Systematische Bestimmung starten", use_container_width=True):
        with st.status("Analysiere Details der Details...") as status:
            
            # Der hierarchische Prompt (Zwingt die KI zum Hinschauen)
            prompt = f"""
            Analysiere diese Münze streng hierarchisch. Durchmesser: {mm_ist:.1f} mm.

            SCHRITT 1: MOTIV-IDENTIFIKATION
            Identifiziere das Hauptmotiv auf beiden Seiten (z.B. Wappen, Adler, Kopf, stehende Figur).

            SCHRITT 2: STRUKTUR-ANALYSE
            - Wappen: Ist der Schild geteilt, geviertelt oder einfach? Beschreibe die Linienführung.
            - Kopf/Figur: Blickrichtung (heraldisch links/rechts)? Stehend, sitzend oder nur Kopf?

            SCHRITT 3: DETAIL DER DETAILS (Tiefenprüfung)
            - Wappen-Inhalte: Was ist exakt in jedem Feld zu sehen? (z.B. "3 Balken", "Löwe mit Doppelschweif", "Kein Adler"). Zähle Elemente.
            - Attribute: Was hält die Figur? (Zepter, Reichsapfel, Waage, Kind, Schwert). 
            - Accessoires: Hat das Motiv eine Krone (welche Art?), einen Bart, eine Brille, langes Haar oder verbundene Augen?
            
            SCHRITT 4: KONTEXT & TEXT
            - Buchstaben/Zahlen: Was steht rundherum? Was steht im Feld oder im Abschnitt (Exergue)?
            - Bringe den Text in direkten Bezug zu den visuellen Details.

            Antworte NUR im JSON-Format:
            {{
              "Bestimmung": "Land, Nominal, Herrscher/Epoche",
              "Wappen_Struktur": "Genaue Feldbeschreibung",
              "Attribute_Details": "Liste von Accessoires und Merkmalen",
              "Legende_Kontext": "Gelesene Zeichen und deren Bedeutung",
              "Handels_Keywords": "Präzise Fachbegriffe für Profi-Suche",
              "Analyse": "Zusammenführung aller Beweise inkl. {mm_ist:.1f}mm"
            }}
            """
            
            try:
                response = client.models.generate_content(
                    model="gemma-3-27b-it",
                    contents=[prompt, img]
                )
                
                # Robustes JSON-Parsing
                text = response.text
                res = json.loads(text[text.find('{'):text.rfind('}')+1])
                st.session_state.analysis_result = res
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- 3. ERGEBNISSE & PROFI-LINKS ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    st.divider()
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.success(f"**Bestimmung:** {res['Bestimmung']}")
        st.write(f"**Wappen-Details:** {res['Wappen_Struktur']}")
        st.write(f"**Merkmale:** {res['Attribute_Details']}")
    with col_res2:
        st.write(f"**Legende:** `{res['Legende_Kontext']}`")
        st.info(f"**Beweisführung:** {res['Analyse']}")

    # Profi-Links (Direkt & Funktionierend)
    st.subheader("🔗 Verifikation auf Fachseiten")
    search_query = f"{res['Bestimmung']} {res['Handels_Keywords']} {mm_ist:.1f}mm"
    q = urllib.parse.quote(search_query)
    
    # Links zu Profi-Datenbanken
    l1, l2, l3 = st.columns(3)
    l1.markdown(f"[📚 **Numista** (Datenbank)](https://en.numista.com/catalogue/index.php?q={q})")
    l2.markdown(f"[💰 **MA-Shops** (Handel)](https://www.ma-shops.de/result.php?searchstr={q})")
    l3.markdown(f"[🖼️ **Google Bilder**](https://www.google.com/search?q={q}&tbm=isch)")
