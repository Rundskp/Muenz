import streamlit as st
from google import genai
from PIL import Image, ImageStat
import urllib.parse
import json

# --- SETUP ---
st.set_page_config(page_title="MuenzID Ultimate", layout="wide")
st.title("🪙 Münz-Detektiv: Hybrid-Engine")

if "result" not in st.session_state:
    st.session_state.result = None

# API: Gemma 3 27B (Hohes Limit, schlaues Modell)
if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API-Key fehlt!")
    st.stop()

# --- 1. ALGORITHMISCHE MATERIAL-ANALYSE (Mathematik statt KI) ---
def analyze_material_math(img):
    # Bild verkleinern für Speed
    small = img.resize((150, 150))
    # In HSV konvertieren (Hue, Saturation, Value)
    hsv = small.convert("HSV")
    
    # Durchschnittswerte berechnen
    stat = ImageStat.Stat(hsv)
    avg_hue = stat.mean[0]        # Farbton (0-255)
    avg_sat = stat.mean[1]        # Sättigung (0-255)
    avg_bri = stat.mean[2]        # Helligkeit (0-255)
    
    # Logik: Silber/Zink/Nickel hat SEHR wenig Sättigung
    if avg_sat < 40: 
        return "Silber / Zink / Nickel (Grau)", "grey"
    
    # Wenn Sättigung hoch ist -> Farbe prüfen
    # Hue ca 20-50 ist Gelb/Orange
    if 15 < avg_hue < 50:
        return "Gold / Messing (Gelb)", "gold"
    
    # Hue < 15 oder > 240 ist oft Rot/Kupfer
    if avg_hue < 15 or avg_hue > 230:
        return "Kupfer / Bronze (Rot)", "copper"
    
    return "Unbestimmtes Metall", "unknown"

# --- UI ---
st.header("Analyse starten")
use_diameter = st.toggle("📏 Durchmesser Filter (Optional)", value=False)
mm_val = "Unbekannt"

if use_diameter:
    size_px = st.slider("Größe", 100, 800, 300)
    if st.button("Kalibrieren 1€ (23.25mm)"):
        st.session_state.ppi = (size_px / 23.25) * 25.4
    if "ppi" in st.session_state:
        mm = (size_px / st.session_state.ppi) * 25.4
        st.caption(f"Wert: {mm:.1f} mm")
        mm_val = f"{mm:.1f}mm"

uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # 1. SOFORTIGE MATERIAL-BERECHNUNG (Vor der KI)
    mat_name, mat_code = analyze_material_math(raw_img)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(raw_img, caption="Original", width=250)
    with c2:
        st.info(f"🧬 **Material-Scan (Math):** {mat_name}")
        st.caption("Basierend auf Pixel-Sättigung, nicht KI-Raten.")

    if st.button("🚀 Scannen & 'Google-Dork' Link bauen", use_container_width=True):
        with st.status("Extrahiere Text für Präzisions-Suche...") as status:
            
            # Der Prompt fragt NICHT nach dem Namen, sondern nur nach Text für die Suche
            prompt = f"""
            Du bist ein OCR-Scanner für Münzen.
            
            DEINE AUFGABE:
            Lies JEDEN lesbaren Buchstaben auf der Münze. Sei präzise.
            Ignoriere das Material (das wurde bereits extern bestimmt: {mat_name}).
            
            1. Transkribiere die Legende (Umschrift). 
               Beispiel: "ARCHID AVST DVX BOHEMIAE" oder "REPUBLIK ÖSTERREICH".
            2. Suche nach Jahreszahlen (z.B. 1620, 1957).
            3. Beschreibe das Wappen kurz (z.B. "Adler", "Löwe").

            Antworte NUR als JSON:
            {{
                "Exakter_Text": "Der gelesene Text",
                "Such_String": "Nur die klarsten 3-4 Wörter für eine Google Suche (z.B. 'ARCHID AVST DVX')",
                "Motiv": "Kurzbeschreibung"
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
                st.session_state.mat_result = mat_name # Speichere das Mathe-Ergebnis
                status.update(label="Fertig!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")

# --- ERGEBNIS ---
if st.session_state.result:
    r = st.session_state.result
    mat = st.session_state.mat_result
    st.divider()
    
    st.write(f"**Gelesener Text:** `{r.get('Exakter_Text')}`")
    st.write(f"**Motiv:** {r.get('Motiv')}")
    
    # DER PERFEKTE SUCHERGEBNIS-LINK ("Google Dorking")
    # Wir bauen eine Suche, die NUR auf Numista sucht und das Material erzwingt.
    # Syntax: site:en.numista.com "SUCHWORTE" metal_type
    
    search_keywords = r.get('Such_String')
    
    # Bestimme englisches Materialwort für die Suche
    metal_search = "Silver" if "Silber" in mat else "Gold" if "Gold" in mat else "Copper"
    
    # Der Trick: Wir suchen spezifisch auf der besten Datenbank der Welt
    query_numista = f'site:en.numista.com "{search_keywords}" {metal_search}'
    link_numista = f"https://www.google.com/search?q={urllib.parse.quote(query_numista)}"
    
    # Fallback: Google Bildersuche
    query_google = f'{search_keywords} coin {metal_search} {mm_val if "Unbekannt" not in mm_val else ""}'
    link_google = f"https://www.google.com/search?q={urllib.parse.quote(query_google)}&tbm=isch"
    
    st.markdown("### 🎯 Ergebnis-Treffer")
    st.success("Klicke hier für die exakte Bestimmung:")
    
    c1, c2 = st.columns(2)
    c1.markdown(f"👉 [**Exakter Datenbank-Match (Numista)**]({link_numista})")
    c2.markdown(f"👉 [**Visueller Vergleich (Google Bilder)**]({link_google})")
    
    st.caption(f"Generierter Such-Code: `{query_numista}`")
    
    if st.button("Neu"):
        st.session_state.result = None
        st.rerun()
