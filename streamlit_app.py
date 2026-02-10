import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance
import json
import urllib.parse

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Experte", layout="wide")
st.title("🪙 Münz-Detektiv: Systematische Identifikation")

# Session State für Kalibrierung
if "ppi" not in st.session_state:
    st.session_state.ppi = 160  # Standard-Startwert

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemma-3-27b')
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. KALIBRIERUNG (Zentrum der App) ---
st.header("📏 1. Kalibrierung & Messung")
st.info("Lege eine Referenzmünze auf den Bildschirm und stelle den Regler so ein, dass der Kreis sie exakt umschließt.")

col_cal1, col_cal2, col_cal3 = st.columns([2, 1, 1])

with col_cal1:
    size_px = st.slider("Kreisgröße anpassen", 50, 800, 200, key="slider_size")

with col_cal2:
    if st.button("📍 Kalibrieren mit 1 €", use_container_width=True):
        # 1 Euro = 23.25 mm
        st.session_state.ppi = (size_px / 23.25) * 25.4
        st.success(f"Kalibriert: {st.session_state.ppi:.1f} PPI")

with col_cal3:
    if st.button("📍 Kalibrieren mit 2 €", use_container_width=True):
        # 2 Euro = 25.75 mm
        st.session_state.ppi = (size_px / 25.75) * 25.4
        st.success(f"Kalibriert: {st.session_state.ppi:.1f} PPI")

# Berechnung des aktuellen Durchmessers auf dem Schirm
mm_ist = (size_px / st.session_state.ppi) * 25.4
st.metric("Gemessener Durchmesser", f"{mm_ist:.2f} mm")

# Visueller Messkreis (Unveränderlicher Mittelpunkt)
st.markdown(f"""
    <div style="display: flex; justify-content: center; padding: 20px; background: #1e1e1e; border-radius: 15px;">
        <div style="width:{size_px}px; height:{size_px}px; border:4px solid gold; border-radius:50%; display: flex; align-items: center; justify-content: center; transition: 0.1s;">
            <div style="width: 4px; height: 4px; background: red; border-radius: 50%;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 2. ANALYSE-MODUS ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild für die Detailsuche hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Zu analysierendes Bild", width=400)

    if st.button("🚀 Systematische Bestimmung starten"):
        with st.status("Hierarchische Analyse läuft...") as status:
            
            # Professioneller, hierarchischer Prompt
            prompt = f"""
            Du bist ein numismatischer Gutachter. Der gemessene Durchmesser beträgt {mm_ist:.1f} mm.
            Analysiere das Bild streng hierarchisch:

            1. MOTIV-TYP: Bestimme das Hauptmotiv (Wappen, Adler, Gesicht/Portrait, Figur, Zahl, Symbol).
            2. STRUKTUR: 
               - Wappen: Geteilt, geviertelt oder einfach? 
               - Adler: Blickrichtung (links/rechts), Flügelhaltung?
               - Gesicht: Profil oder frontal? Blickrichtung?
               - Figur: Stehend, sitzend, reitend?
            3. FEIN-DETAILS:
               - Symbole: Was ist in jedem Feld/Teil zu sehen? Wie oft (z.B. 3 Löwen)?
               - Accessoires: Krone, Zepter, Reichsapfel, Schwert, Waage, Kind, verbundene Augen?
               - Merkmale: Bart, Brille, Haarlänge, markante Nase?
            4. LEGENDE: Welche Buchstaben/Zahlen sind wo (Umlaufend, Mitte, Exergue)? Setze sie in Kontext zum Motiv.

            Antworte NUR im JSON-Format:
            {{
              "Identität": "Land, Nominal, Herrscher/Ära",
              "Motiv_Struktur": "Beschreibung der Anordnung und Blickrichtungen",
              "Fein_Details": "Liste aller Symbole, Accessoires und Merkmale",
              "Legende_Kontext": "Gelesene Zeichen und deren Bedeutung",
              "Handels_Keywords": "Präzise Fachbegriffe für Profi-Suche",
              "Begruendung": "Zusammenführung von Bilddetails und Durchmesser ({mm_ist:.1f} mm)"
            }}
            """
            
            try:
                # Bildverbesserung (Silent)
                enhanced = ImageEnhance.Contrast(img).enhance(1.8)
                response = model.generate_content([prompt, enhanced])
                
                # JSON-Parsing
                content = response.text
                res = json.loads(content[content.find('{'):content.rfind('}')+1])
                
                status.update(label="Analyse abgeschlossen!", state="complete")
                
                # --- 3. ERGEBNISSE ---
                st.divider()
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("Befund")
                    st.success(f"**Bestimmung:** {res['Identität']}")
                    st.write(f"**Struktur:** {res['Motiv_Struktur']}")
                    st.write(f"**Details:** {res['Fein_Details']}")
                with col_b:
                    st.subheader("Kontext")
                    st.write(f"**Legende:** `{res['Legende_Kontext']}`")
                    st.info(f"**Experten-Urteil:** {res['Begruendung']}")

                # --- 4. PROFI-LINKS (Präzise generiert) ---
                st.subheader("🔗 Verifikation auf Fachplattformen")
                
                # Erstellung eines extrem präzisen Suchstrings
                search_term = f"{res['Identität']} {res['Handels_Keywords']} {mm_ist:.1f}mm"
                q = urllib.parse.quote(search_term)
                
                l1, l2, l3 = st.columns(3)
                l1.markdown(f"[📚 **Numista** (Typen-Check)](https://en.numista.com/catalogue/index.php?q={q})")
                l2.markdown(f"[💰 **MA-Shops** (Handelspreise)](https://www.ma-shops.de/result.php?searchstr={q})")
                l3.markdown(f"[🖼️ **Google Bilder** (Abgleich)](https://www.google.com/search?q={q}&tbm=isch)")
                
                st.caption(f"Verwendeter Suchbegriff: {search_term}")

            except Exception as e:
                st.error(f"Fehler im System: {e}")
