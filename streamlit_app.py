import streamlit as st
from google import genai
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import json
import urllib.parse
import io

# --- SETUP ---
st.set_page_config(page_title="MuenzID Pro - Expert Modus", layout="wide")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# Client Setup
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 1. KALIBRIERUNG (Unverändert wichtig für mm-Bestimmung) ---
st.header("📏 1. Kalibrierung")
size_px = st.slider("Kreisgröße", 100, 800, 300)
# (Kalibrierungs-Logik wie zuvor...)

# --- 2. BILD-OPTIMIERUNG (Der Kern der Verbesserung) ---
st.header("🔍 2. Bild-Analyse")
uploaded_file = st.file_uploader("Münzbild (auch schlechte Qualität)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    raw_img = Image.open(uploaded_file)
    
    # --- SPEZIAL-FILTER FÜR SCHLECHTE BILDER ---
    # Schritt A: Graustufen & Normalisierung (Entfernt Farbrauschen)
    proc = ImageOps.grayscale(raw_img)
    proc = ImageOps.autocontrast(proc, cutoff=2) # Spreizt die Helligkeit
    
    # Schritt B: Kanten-Verstärkung (Findet Relief-Strukturen)
    # Wir nutzen einen Unsharp-Mask-Effekt für die "Knochen" der Münze
    proc = proc.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    # Schritt C: Lokale Kontrast-Anhebung
    proc = ImageEnhance.Contrast(proc).enhance(1.8)

    st.image([raw_img, proc], caption=["Original", "KI-Optimiert (Struktur-Fokus)"], width=400)

    if st.button("🚀 Systematische Bestimmung starten"):
        with st.status("Extrahiere Details aus abgenutzter Oberfläche...") as status:
            
            prompt = f"""
            Du bist ein numismatischer Forensiker. Die Münze ist stark abgenutzt.
            Durchmesser: {mm_ist:.1f} mm.

            DEIN ARBEITSABLAUF:
            1. SILHOUETTEN-CHECK: Ignoriere Schatten, suche nach Umrissen. (z.B. Schreitende Person, Adler-Symmetrie).
            2. RELIEF-RELIKTE: Suche nach einzelnen Buchstabenresten (S, G, K, R) oder Zahlen (1, 2, 5, 10).
            3. NEGATIV-AUSSCHLUSS: Wenn du eine '1' siehst und das Bild aus Österreich kommt, prüfe ob daneben ein 'S' (Schilling) oder 'G' (Groschen) sein könnte, auch wenn nur Schatten da sind.
            4. KEINE HALLUZINATION: Beschreibe nur Formen. Wenn ein Arm wie ein 'Alpenhorn' aussieht, prüfe ob es ein 'Sämann' (Sower) sein könnte.

            Antworte als JSON:
            {{
              "Bestimmung": "Land, Nominal, Ära",
              "Motiv_Struktur": "Genaue Beschreibung der Umrisse",
              "Gelesene_Fragmente": "Was ist sicher, was ist vermutet?",
              "Handels_Keywords": "Präzise Suchbegriffe für abgenutzte Stücke",
              "Analyse": "Warum passt das zu {mm_ist:.1f} mm?"
            }}
            """
            
            # Sende das optimierte Bild (proc) an die KI
            response = client.models.generate_content(
                model="gemma-3-27b-it",
                contents=[prompt, proc]
            )
            
            # (JSON Parsing & Anzeige wie gehabt...)

                
                txt = response.text
                start, end = txt.find('{'), txt.rfind('}') + 1
                st.session_state.result = json.loads(txt[start:end])
                status.update(label="Analyse abgeschlossen!", state="complete")
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.write(response.text if 'response' in locals() else "Keine API-Antwort.")

# --- 3. ERGEBNIS-ANZEIGE ---
if st.session_state.result:
    res = st.session_state.result
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"**Bestimmung:** {res['Bestimmung']}")
        st.write(f"**Motiv & Struktur:** {res['Motiv_Struktur']}")
        st.write(f"**Details:** {res['Fein_Details']}")
    with col_b:
        # Anzeige ändert sich je nach Lesbarkeit
        if "[unleserlich]" in res['Legende_Status']:
             st.warning(f"**Legende (Abgenutzt):** `{res['Legende_Status']}`")
        else:
             st.write(f"**Legende (Gelesen):** `{res['Legende_Status']}`")
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
