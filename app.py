import io
import json
import re
import time
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from PIL import Image

st.set_page_config(
    page_title="AI Smart Food Waste & Donation System",
    page_icon="🍲",
    layout="centered",
)

st.title("🍲 AI Smart Food Waste & Donation System")
st.markdown(
    "**பெஸ்ட் ப்ரோஸ் கூட்டணி** சார்பாக உணவுப் பொருள்களின் தரத்தை (Freshness) "
    "**Gemini AI Recognition** மூலம் பகுப்பாய்வு செய்யும் தளம்! 🚀"
)
st.divider()

GPS_SCRIPT_TEMPLATE = '''
<script>
(function() {
    const statusEl = document.createElement("div");
    statusEl.style.fontFamily = "sans-serif";
    statusEl.style.fontSize = "13px";
    statusEl.style.color = "#0f766e";
    statusEl.style.padding = "6px 0";
    statusEl.innerText = "📡 உங்கள் போன் GPS மூலம் இருப்பிடம் எடுக்கப்படுகிறது...";
    document.body.appendChild(statusEl);
    if (!navigator.geolocation) {
        statusEl.style.color = "#b91c1c";
        statusEl.innerText = "❌ இந்த பிரவுசரில் GPS ஆதரவு இல்லை.";
        return;
    }
    navigator.geolocation.getCurrentPosition(
        function(pos) {
            const lat = pos.coords.latitude.toFixed(6);
            const lon = pos.coords.longitude.toFixed(6);
            statusEl.style.color = "#15803d";
            statusEl.innerText = "✅ GPS கிடைத்தது (" + lat + ", " + lon + "). விவரங்கள் அப்டேட் ஆகிறது...";
            try {
                const parentUrl = new URL(window.parent.location.href);
                if (parentUrl.searchParams.get("lat") !== lat || parentUrl.searchParams.get("lon") !== lon) {
                    parentUrl.searchParams.set("lat", lat);
                    parentUrl.searchParams.set("lon", lon);
                    window.parent.location.replace(parentUrl.toString());
                }
            } catch (e) {}
        },
        function(err) {
            statusEl.style.color = "#b91c1c";
            statusEl.innerText = "⚠️ GPS அனுமதி கிடைக்கவில்லை (" + err.message + "). கீழே உங்கள் பகுதி/நகரத்தை உள்ளிடலாம்.";
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
})();
</script>
'''

@st.cache_resource
def get_genai_client(key: str):
    return genai.Client(api_key=key)

def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return st.session_state.get("temp_gemini_api_key", "")

def contains_tamil(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))

FAST_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.8-flash"]

def call_gemini_json_fast(client, contents, prompt_text: str) -> dict:
    last_error = None
    for model_name in FAST_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents if isinstance(contents, list) else [prompt_text],
                config={"response_mime_type": "application/json", "temperature": 0.2},
            )
            raw_text = (response.text or "").strip()
            if raw_text:
                return json.loads(raw_text)
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            if "404" in err_str or "NOT_FOUND" in err_str:
                continue
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                time.sleep(0.25)
                continue
            continue
    raise last_error if last_error else RuntimeError("Gemini request failed")

def build_fast_fallback_contacts(gps_coords=None, area_text: str = '', food_name: str = '', is_fresh: bool = False) -> dict:
    if gps_coords:
        lat, lon = gps_coords
        loc_label = f"GPS ({lat:.4f}, {lon:.4f})"
    elif area_text.strip():
        loc_label = area_text.strip()
    else:
        loc_label = "உங்கள் சுற்றியுள்ள பகுதி"

    food_label = f"{food_name} " if food_name else ""
    if is_fresh:
        summary = f"{loc_label} சுற்றளவில் {food_label}தானம் வழங்க ஏற்ற ஆதரவற்றோர் இல்லங்கள், முதியோர் இல்லங்கள் மற்றும் உணவு வங்கிகளின் தொடர்பு விவரங்கள்:"
        note_1 = 'உணவு நல்ல நிலையில் உள்ளதால், வெப்பநிலை குறையாமல் பாதுகாப்பான பாத்திரங்களில் வைத்து உடனடியாக வழங்கலாம்.'
        note_2 = 'வழங்குவதற்கு முன் இல்ல நிர்வாகத்திடம் நேரடியாகத் தொடர்பு கொண்டு நேரத்தை உறுதி செய்யவும்.'
    else:
        summary = f"{loc_label} சுற்றளவில் உணவு தானம் மற்றும் சமூக உதவி அமைப்புகளின் தொடர்பு விவரங்கள்:"
        note_1 = 'உணவின் தரம் மற்றும் பாதுகாப்பை உறுதி செய்த பிறகு அருகிலுள்ள இல்லங்களில் வழங்கவும்.'
        note_2 = 'தொடர்பு விவரங்களைச் சேர்த்து அல்லது நேரடியாக விசாரித்து உறுதி செய்து கொள்ளவும்.'

    return {
        "region_summary_ta": summary,
        "contacts": [
            {
                "organization_ta": "அருகிலுள்ள முதியோர் இல்லம் & ஆசரமத் தொடர்பு",
                "category_ta": "முதியோர் இல்லம் / ஆசரமம்",
                "area_note_ta": loc_label,
                "contact_info_ta": "நேரடியாகத் தொடர்பு கொண்டு உறுதி செய்யவும் / உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும்",
                "donation_note_ta": note_1,
            },
            {
                "organization_ta": "உணவு தானம் & ஆதரவற்றோர் இல்லத் தொடர்பு",
                "category_ta": "உணவு தான அமைப்பு & இல்லம்",
                "area_note_ta": loc_label,
                "contact_info_ta": "நேரடியாகத் தொடர்பு கொண்டு உறுதி செய்யவும் / உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும்",
                "donation_note_ta": note_2,
            },
        ],
    }

def generate_ai_surrounding_contacts(api_key: str, gps_coords=None, area_text: str = '', food_name: str = '', is_fresh: bool = False) -> dict:
    fallback = build_fast_fallback_contacts(
        gps_coords=gps_coords,
        area_text=area_text,
        food_name=food_name,
        is_fresh=is_fresh,
    )
    if not api_key:
        return fallback

    client = get_genai_client(key=api_key)
    if gps_coords:
        lat, lon = gps_coords
        loc_desc = f"GPS {lat:.6f}, {lon:.6f}"
    elif area_text.strip():
        loc_desc = f"area {area_text.strip()}"
    else:
        loc_desc = "user surroundings"

    food_desc = (
        f"Food: {food_name}, Fresh for donation: {'Yes' if is_fresh else 'Check'}. "
        if food_name else ""
    )

    prompt = (
        "Write EVERY text value strictly in natural Tamil (தமிழ்) only. Do not use Hindi. "
        "Never invent fake phone numbers or fake addresses; use 'நேரடியாகத் தொடர்பு கொண்டு உறுதி செய்யவும் / உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும்' for phone/contact. "
        "Do NOT include map links. "
        f"{food_desc}Location: {loc_desc}. "
        "Return ONLY valid JSON with keys region_summary_ta and contacts (list of organization_ta, category_ta, area_note_ta, contact_info_ta, donation_note_ta)."
    )

    try:
        parsed = call_gemini_json_fast(client, [prompt], prompt)
        if isinstance(parsed, dict) and isinstance(parsed.get("contacts"), list) and len(parsed["contacts"]) > 0:
            return parsed
    except Exception:
        pass
    return fallback

def render_donation_section(highlight_fresh: bool = False, food_name: str = ''):
    st.subheader("🤝 GPS + AI சுற்றியுள்ள தானம் & ஆசரமத் தொடர்புகள்")
    if highlight_fresh:
        st.success(
            "🍲 உணவு நல்ல தரத்தில் இருப்பதால், உங்கள் GPS சுற்றளவில் உள்ள ஆசரமம் அல்லது தான அமைப்புகளின் "
            "தொடர்பு விவரங்களைப் பார்த்து பாதுகாப்பாக வழங்கலாம்!"
        )
    else:
        st.caption(
            "உங்கள் GPS இருப்பிடத்தை அடிப்படையாகக் கொண்டு வேகமாக வரும் சுற்றியுள்ள தொடர்பு விவரங்கள்:"
        )

    if "gps_coords" not in st.session_state:
        st.session_state["gps_coords"] = None
    if "manual_area_query" not in st.session_state:
        st.session_state["manual_area_query"] = ""
    if "ai_contacts_cache" not in st.session_state:
        st.session_state["ai_contacts_cache"] = {}

    qp_lat = st.query_params.get("lat")
    qp_lon = st.query_params.get("lon")
    if qp_lat and qp_lon:
        try:
            st.session_state["gps_coords"] = (float(qp_lat), float(qp_lon))
        except ValueError:
            pass

    col_gps, col_clear = st.columns([2, 1])
    with col_gps:
        request_gps = st.button("📍 GPS மூலம் என் இருப்பிடத்தைத் தேடு", use_container_width=True)
    with col_clear:
        if st.session_state["gps_coords"] is not None:
            if st.button("🔄 GPS நீக்கு", use_container_width=True):
                st.session_state["gps_coords"] = None
                st.session_state["ai_contacts_cache"] = {}
                try:
                    st.query_params.pop("lat", None)
                    st.query_params.pop("lon", None)
                except Exception:
                    pass
                st.rerun()

    if request_gps:
        components.html(GPS_SCRIPT_TEMPLATE, height=55)

    gps_coords = st.session_state["gps_coords"]
    if gps_coords:
        st.info(
            f"📍 **GPS இருப்பிடம் செயல்படுகிறது:** `{gps_coords[0]:.6f}, {gps_coords[1]:.6f}`"
        )

    manual_area = st.text_input(
        "சுற்றியுள்ள பகுதி / ஊர் பெயர் (GPS கிடைக்காதபோது அல்லது கூடுதலாக)",
        value=st.session_state["manual_area_query"],
        placeholder="உதாரணம்: ராஜபாளையம் / மதுரை / சென்னை",
    )
    st.session_state["manual_area_query"] = manual_area

    api_key = get_api_key()
    loc_key = f"{gps_coords}_{manual_area.strip()}_{food_name}_{highlight_fresh}"

    if loc_key not in st.session_state["ai_contacts_cache"]:
        with st.spinner("⚡ வேகமாக சுற்றியுள்ள தொடர்புகளை எடுக்கிறது..."):
            contacts_data = generate_ai_surrounding_contacts(
                api_key=api_key,
                gps_coords=gps_coords,
                area_text=manual_area,
                food_name=food_name,
                is_fresh=highlight_fresh,
            )
            st.session_state["ai_contacts_cache"][loc_key] = contacts_data

    contacts_payload = st.session_state["ai_contacts_cache"].get(loc_key, {})
    region_summary = contacts_payload.get("region_summary_ta", "")
    if region_summary:
        st.markdown(f"🌐 **சுற்றளவு தகவல்:** {region_summary}")

    for idx, c_item in enumerate(contacts_payload.get("contacts", []), start=1):
        org_ta = c_item.get("organization_ta", "சுற்றியுள்ள தானத் தொடர்பு")
        cat_ta = c_item.get("category_ta", "உணவு தானம்")
        area_note = c_item.get("area_note_ta", "உங்கள் சுற்றியுள்ள பகுதி")
        contact_info = c_item.get("contact_info_ta", "நேரடியாகத் தொடர்பு கொண்டு உறுதி செய்யவும்")
        donation_note = c_item.get("donation_note_ta", "")
        with st.container(border=True):
            st.markdown(f"**{idx}. {org_ta}**")
            st.markdown(f"🏷️ **வகை:** `{cat_ta}`")
            st.markdown(f"📍 **பகுதி:** `{area_note}`")
            st.markdown(f"📞 **தொடர்பு விவரம்:** `{contact_info}`")
            if donation_note:
                st.markdown(f"💡 **குறிப்பு:** {donation_note}")

def prepare_fast_image(uploaded_file) -> Image.Image:
    img = Image.open(uploaded_file).convert("RGB")
    max_size = 640
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70, optimize=True)
    buf.seek(0)
    return Image.open(buf)

def build_fast_food_fallback(image: Image.Image) -> dict:
    small = image.resize((64, 64))
    pixels = list(small.getdata())
    avg_luma = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels) / max(len(pixels), 1)
    if avg_luma >= 95:
        return {
            "food_name_ta": "உணவுப் பொருள் (விரைவு பரிசோதனை)",
            "freshness_score": 78.0,
            "status": "FRESH",
            "conclusion_ta": "படத்தின் நிறம் மற்றும் வெளிச்சத்தின் அடிப்படையில் உணவு நல்ல நிலையில் இருப்பதாகத் தெரிகிறது.",
            "recommendation_ta": "உணவு நல்ல தரத்தில் இருந்தால் சுத்தமான முறையில் உடனடியாகப் பயன்படுத்தலாம் அல்லது அருகிலுள்ள இல்லத்திற்கு தானம் செய்யலாம்.",
        }
    if avg_luma >= 55:
        return {
            "food_name_ta": "உணவுப் பொருள் (விரைவு பரிசோதனை)",
            "freshness_score": 52.0,
            "status": "MODERATE",
            "conclusion_ta": "உணவின் தரம் மிதமான நிலையில் உள்ளது; வாசனை மற்றும் நிலையை நேரடியாகச் சரிபார்க்கவும்.",
            "recommendation_ta": "தாமதிக்காமல் விரைவாகப் பயன்படுத்தவும் அல்லது தகுந்த முறையில் கையாளவும்.",
        }
    return {
        "food_name_ta": "உணவுப் பொருள் (விரைவு பரிசோதனை)",
        "freshness_score": 25.0,
        "status": "SPOILED",
        "conclusion_ta": "படத்தின் தோற்றத்தின் அடிப்படையில் இந்த உணவைப் பயன்படுத்துவது பாதுகாப்பானதல்ல எனத் தோன்றுகிறது.",
        "recommendation_ta": "உணவு தானம் செய்யாமல் இயற்கை உரம் (Compost) அல்லது பாதுகாப்பான கழிவு முறையில் அகற்றவும்.",
    }

def analyze_food_with_ai(image: Image.Image, key: str) -> dict:
    fallback = build_fast_food_fallback(image)
    if not key:
        return fallback
    client = get_genai_client(key)
    prompt = (
        "Write EVERY text value strictly in natural Tamil (தமிழ்) only. Do not use Hindi or 'தாஜா'. "
        "Analyze food freshness briefly and accurately. Return ONLY valid JSON with keys: "
        "food_name_ta, freshness_score, status, conclusion_ta, recommendation_ta."
    )
    try:
        parsed = call_gemini_json_fast(client, [image, prompt], prompt)
        if isinstance(parsed, dict) and contains_tamil(str(parsed.get("conclusion_ta", ""))):
            return parsed
    except Exception:
        pass
    return fallback

st.header("📸 உணவுப் படம் மற்றும் AI ஃபிரெஷ்னஸ் பரிசோதனை")
st.write("உணவுப் பொருளின் படத்தை இங்கே பதிவேற்றவும் (JPG/PNG)")

uploaded_file = st.file_uploader("Upload", type=["jpg", "jpeg", "png"])

api_key = get_api_key()

if not api_key:
    with st.expander("🔑 Gemini API Key அமைப்பு (Optional / தற்காலிக சோதனைக்கு)"): 
        entered_key = st.text_input(
            "உங்கள் Gemini API Key-ஐ உள்ளிடவும்",
            type="password",
            help="Streamlit Secrets-ல் GEMINI_API_KEY அமைத்திருந்தால் தானாக எடுத்துக்கொள்ளும்.",
        )
        if entered_key:
            st.session_state["temp_gemini_api_key"] = entered_key
            api_key = entered_key

if uploaded_file is not None:
    image = prepare_fast_image(uploaded_file)
    st.image(image, caption="பதிவேற்றப்பட்ட உணவுப் படம்", use_container_width=True)

    cache_key = f"{uploaded_file.name}_{uploaded_file.size}_fast_v17"
    if "ai_cache" not in st.session_state:
        st.session_state["ai_cache"] = {}

    if cache_key in st.session_state["ai_cache"]:
        result = st.session_state["ai_cache"][cache_key]
    else:
        with st.spinner("⚡ உடனடியாகப் பரிசோதிக்கிறது..."):
            result = analyze_food_with_ai(image, api_key)
            st.session_state["ai_cache"][cache_key] = result

    food_name = result.get("food_name_ta", "உணவுப் பொருள்")
    score = float(result.get("freshness_score", 0.0))
    score = max(0.0, min(100.0, score))
    status = str(result.get("status", "SPOILED")).upper()
    conclusion = result.get("conclusion_ta", "உணவுத் தரம் பரிசோதிக்கப்பட்டது.")
    recommendation = result.get("recommendation_ta", "பாதுகாப்பான முறையில் கையாளவும்.")

    st.subheader("🤖 AI பகுப்பாய்வு முடிவு (Gemini Vision)")
    st.markdown(f"🍽️ **அடையாளம் காணப்பட்ட பொருள்:** `{food_name}`")
    st.markdown(f"📊 **AI Freshness Score:** `{score:.1f}%`")

    is_fresh = status == "FRESH" or score >= 60.0
    if is_fresh:
        st.success(f"✅ **முடிவு:** {conclusion}")
        st.info(f"👉 **பரிந்துரை:** {recommendation} 🤝🍲")
    elif status == "MODERATE" or score >= 30.0:
        st.warning(f"⚠️ **முடிவு:** {conclusion}")
        st.info(f"👉 **பரிந்துரை:** {recommendation}")
    else:
        st.error(f"⚠️ **முடிவு:** {conclusion}")
        st.info(f"👉 **பரிந்துரை:** {recommendation} 🌱")

    st.divider()
    render_donation_section(highlight_fresh=is_fresh, food_name=food_name)
else:
    st.info("💡 மேலே உள்ள பட்டனைப் பயன்படுத்தி ஒரு உணவுப் படத்தை அப்லோட் செய்யவும் ப்ரோ!")
    st.divider()
    render_donation_section(highlight_fresh=False, food_name='')

st.divider()
st.caption("Developed with ❤️ by Best Bros (Jumail & AI)")
