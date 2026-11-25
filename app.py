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
    statusEl.innerText = "📡 உங்கள் போன் GPS மூலம் சுற்றியுள்ள இடம் கண்டறியப்படுகிறது...";
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
            statusEl.innerText = "✅ GPS கிடைத்தது (" + lat + ", " + lon + "). பக்கத்தை ஒருமுறை ரீஃப்ரெஷ் செய்து அருகிலுள்ள தொடர்புகளைப் பாருங்கள்!";
            try {
                const parentUrl = new URL(window.parent.location.href);
                parentUrl.searchParams.set("lat", lat);
                parentUrl.searchParams.set("lon", lon);
                window.parent.history.replaceState({}, , parentUrl.toString());
            } catch (e) {}
        },
        function(err) {
            statusEl.style.color = "#b91c1c";
            statusEl.innerText = "⚠️ GPS அனுமதி கிடைக்கவில்லை (" + err.message + "). கீழே உங்கள் பகுதி/நகரத்தை உள்ளிடலாம்.";
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
})();
</script>
'''

def get_genai_client(key: str):
    return genai.Client(api_key=key)

def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return st.session_state.get("temp_gemini_api_key", "")

def generate_ai_surrounding_contacts(api_key: str, gps_coords=None, area_text: str = '', food_name: str = '', is_fresh: bool = False) -> dict:
    client = get_genai_client(key=api_key)
    if gps_coords:
        lat, lon = gps_coords
        loc_desc = f"GPS coordinates latitude {lat:.6f}, longitude {lon:.6f}"
    elif area_text.strip():
        loc_desc = f"area/city: {area_text.strip()}"
    else:
        loc_desc = "nearby surroundings in the user's current area"

    food_context = (
        f"Analyzed food item: {food_name} (Freshness: {'Good/Fresh for donation' if is_fresh else 'General check'}). "
        if food_name else "General surplus food donation check. "
    )

    prompt = (
        "CRITICAL LANGUAGE RULE: Write EVERY text field strictly in natural Tamil script (தமிழ்). "
        "Do not use Hindi or other Indian languages. "
        f"Based on {loc_desc} and {food_context}, suggest surrounding food donation contacts/organizations, "
        "ashrams, old age homes, orphanages, or community food banks around the user's surroundings. "
        "IMPORTANT: Do NOT invent fake phone numbers or fake street addresses. Where real contact details need to be verified or added, "
        "clearly write 'நேரடியாகத் தொடர்பு கொண்டு உறுதி செய்யவும் / உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும்' instead of any made-up number. "
        'Do NOT include any map links or map search queries.\n'
        "Return ONLY valid JSON with keys: region_summary_ta (string), contacts (list of objects with keys: "
        "organization_ta, category_ta, area_note_ta, contact_info_ta, donation_note_ta)."
    )

    dynamic_models = []
    try:
        for m in client.models.list():
            m_name = getattr(m, "name", "")
            clean_name = m_name.replace("models/", "") if m_name else ""
            if "gemini" in clean_name and "flash" in clean_name:
                if clean_name not in dynamic_models:
                    dynamic_models.append(clean_name)
    except Exception:
        pass

    candidate_models = []
    for preferred in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if preferred not in candidate_models:
            candidate_models.append(preferred)
    for dm in dynamic_models:
        if dm not in candidate_models:
            candidate_models.append(dm)

    last_error = None
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                raw_text = (response.text or "").strip()
                return json.loads(raw_text)
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "404" in err_str or "NOT_FOUND" in err_str:
                    break
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break
    raise last_error if last_error else RuntimeError("AI surrounding contacts failed")

def render_donation_section(highlight_fresh: bool = False, food_name: str = ''):
    st.subheader("🤝 GPS + AI சுற்றியுள்ள தானம் & ஆசரமத் தொடர்புகள்")
    if highlight_fresh:
        st.success(
            "🍲 உணவு நல்ல தரத்தில் இருப்பதால், உங்கள் GPS சுற்றளவில் உள்ள ஆசரமம் அல்லது தான அமைப்புகளின் "
            "தொடர்பு விவரங்களைப் பார்த்து பாதுகாப்பாக வழங்கலாம்!"
        )
    else:
        st.caption(
            "உங்கள் GPS இருப்பிடத்தை அடிப்படையாகக் கொண்டு AI காட்டும் சுற்றியுள்ள தொடர்பு விவரங்கள்:"
        )

    if "gps_coords" not in st.session_state:
        st.session_state["gps_coords"] = None
    if "manual_area_query" not in st.session_state:
        st.session_state["manual_area_query"] = ""
    if "ai_contacts_cache" not in st.session_state:
        st.session_state["ai_contacts_cache"] = {}

    col_gps, col_clear = st.columns([2, 1])
    with col_gps:
        request_gps = st.button("📍 GPS மூலம் என் இருப்பிடத்தைத் தேடு", use_container_width=True)
    with col_clear:
        if st.session_state["gps_coords"] is not None:
            if st.button("🔄 GPS நீக்கு", use_container_width=True):
                st.session_state["gps_coords"] = None
                st.session_state["ai_contacts_cache"] = {}
                st.rerun()

    if request_gps:
        components.html(GPS_SCRIPT_TEMPLATE, height=60)

    qp_lat = st.query_params.get("lat")
    qp_lon = st.query_params.get("lon")
    if qp_lat and qp_lon:
        try:
            st.session_state["gps_coords"] = (float(qp_lat), float(qp_lon))
        except ValueError:
            pass

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

    if not api_key:
        st.warning("🔑 AI மூலம் சுற்றியுள்ள தொடர்புகளைக் காட்ட GEMINI_API_KEY தேவை.")
        fallback_contacts = [
            (
                "அருகிலுள்ள முதியோர் இல்லம் / ஆசரமத் தொடர்பு",
                "முதியோர் இல்லம் & ஆசரமம்",
                "உங்கள் சுற்றியுள்ள பகுதி",
                "உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும் / நேரடியாகத் தொடர்பு கொள்ளவும்",
            ),
            (
                "உணவு தானம் & ஆதரவற்றோர் இல்லத் தொடர்பு",
                "உணவு தான அமைப்பு",
                "உங்கள் சுற்றியுள்ள பகுதி",
                "உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும் / நேரடியாகத் தொடர்பு கொள்ளவும்",
            ),
        ]
        for idx, (org_ta, cat_ta, area_n, info_ta) in enumerate(fallback_contacts, start=1):
            with st.container(border=True):
                st.markdown(f"**{idx}. {org_ta}**")
                st.markdown(f"🏷️ **வகை:** `{cat_ta}`")
                st.markdown(f"📍 **பகுதி:** `{area_n}`")
                st.markdown(f"📞 **தொடர்பு விவரம்:** `{info_ta}`")
        return

    if loc_key not in st.session_state["ai_contacts_cache"]:
        with st.spinner("🤖 GPS அடிப்படையில் சுற்றியுள்ள தொடர்புகளை AI தேடுகிறது..."):
            try:
                ai_contacts_data = generate_ai_surrounding_contacts(
                    api_key=api_key,
                    gps_coords=gps_coords,
                    area_text=manual_area,
                    food_name=food_name,
                    is_fresh=highlight_fresh,
                )
                st.session_state["ai_contacts_cache"][loc_key] = ai_contacts_data
            except Exception as e:
                st.error(f"❌ AI தொடர்புத் தேடலில் பிழை: {e}")
                return

    contacts_payload = st.session_state["ai_contacts_cache"].get(loc_key, {})
    region_summary = contacts_payload.get("region_summary_ta", "")
    if region_summary:
        st.markdown(f"🌐 **AI சுற்றளவு தகவல்:** {region_summary}")

    contacts_list = contacts_payload.get("contacts", [])
    if not contacts_list:
        contacts_list = [
            {
                "organization_ta": "அருகிலுள்ள முதியோர் இல்லம் & ஆசரமத் தொடர்பு",
                "category_ta": "முதியோர் இல்லம் / ஆசரமம்",
                "area_note_ta": "உங்கள் GPS சுற்றியுள்ள பகுதி",
                "contact_info_ta": "உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும் / நேரடியாகத் தொடர்பு கொள்ளவும்",
                "donation_note_ta": "உணவு நல்ல நிலையில் உள்ளதா என்பதை உறுதி செய்து தொடர்பு கொள்ளவும்.",
            },
            {
                "organization_ta": "உணவு தானம் & ஆதரவற்றோர் இல்லத் தொடர்பு",
                "category_ta": "உணவு தான அமைப்பு",
                "area_note_ta": "உங்கள் GPS சுற்றியுள்ள பகுதி",
                "contact_info_ta": "உங்கள் தொடர்பு எண்ணைச் சேர்க்கவும் / நேரடியாகத் தொடர்பு கொள்ளவும்",
                "donation_note_ta": "உணவு வழங்குவதற்கு முன் சம்பந்தப்பட்ட இல்லத்திடம் நேரடியாகப் பேசி உறுதி செய்யவும்.",
            },
        ]

    for idx, c_item in enumerate(contacts_list, start=1):
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
    max_size = 768
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75, optimize=True)
    buf.seek(0)
    return Image.open(buf)

def contains_tamil(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))

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

def analyze_food_with_ai(image: Image.Image, key: str) -> dict:
    client = get_genai_client(key)
    prompt = (
        "CRITICAL LANGUAGE RULE: Write EVERY text field strictly in natural Tamil script (தமிழ்). "
        "Never use Hindi, Sanskrit, Telugu, Kannada, Malayalam, or English words in the values. "
        "For example, use 'புதியது' / 'நல்ல நிலையில் உள்ளது' instead of 'தாஜா'.\n"
        "Analyze the food image briefly and accurately for freshness. Return ONLY valid JSON:\n"
        '{"food_name_ta": "தமிழில் உணவுப் பெயர்", '
        '"freshness_score": 0 to 100 number, '
        '"status": "FRESH" or "MODERATE" or "SPOILED", '
        '"conclusion_ta": "தமிழில் சுருக்கமான முடிவு", '
        '"recommendation_ta": "தானம் அல்லது உடனடி பயன்பாடு அல்லது உரம் பற்றிய சுருக்கமான தமிழ் பரிந்துரை"}'
    )
    dynamic_models = []
    try:
        for m in client.models.list():
            m_name = getattr(m, "name", "")
            clean_name = m_name.replace("models/", "") if m_name else ""
            if "gemini" in clean_name and "flash" in clean_name:
                if clean_name not in dynamic_models:
                    dynamic_models.append(clean_name)
    except Exception:
        pass
    candidate_models = []
    for preferred in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if preferred not in candidate_models:
            candidate_models.append(preferred)
    for dm in dynamic_models:
        if dm not in candidate_models:
            candidate_models.append(dm)
    last_error = None
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[image, prompt],
                    config={"response_mime_type": "application/json"},
                )
                raw_text = (response.text or "").strip()
                parsed = json.loads(raw_text)
                if contains_tamil(str(parsed.get("conclusion_ta", ""))):
                    return parsed
                retry_resp = client.models.generate_content(
                    model=model_name,
                    contents=[
                        image,
                        "Rewrite all text fields strictly in Tamil (தமிழ்) only. Return ONLY valid JSON with keys: "
                        "food_name_ta, freshness_score, status, conclusion_ta, recommendation_ta.",
                    ],
                    config={"response_mime_type": "application/json"},
                )
                return json.loads((retry_resp.text or '').strip())
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "404" in err_str or "NOT_FOUND" in err_str:
                    break
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break
    raise last_error if last_error else RuntimeError("AI analysis failed")

if uploaded_file is not None:
    image = prepare_fast_image(uploaded_file)
    st.image(image, caption="பதிவேற்றப்பட்ட உணவுப் படம்", use_container_width=True)
    if not api_key:
        st.error(
            "⚠️ **GEMINI_API_KEY கிடைக்கவில்லை!** Streamlit Secrets-ல் `GEMINI_API_KEY` "
            "சேர்க்கவும் அல்லது மேலே உள்ள 'Gemini API Key அமைப்பு' பகுதியில் தற்காலிகமாக உள்ளிடவும்."
        )
    else:
        cache_key = f"{uploaded_file.name}_{uploaded_file.size}_ta_v15"
        if "ai_cache" not in st.session_state:
            st.session_state["ai_cache"] = {}
        if cache_key in st.session_state["ai_cache"]:
            result = st.session_state["ai_cache"][cache_key]
        else:
            with st.spinner("⚡ தமிழில் வேகமாக AI பகுப்பாய்வு செய்கிறது..."):
                try:
                    result = analyze_food_with_ai(image, api_key)
                    st.session_state["ai_cache"][cache_key] = result
                except Exception as e:
                    st.error(f"❌ AI பகுப்பாய்வில் பிழை ஏற்பட்டது: {e}")
                    result = None
        if result is not None:
            food_name = result.get("food_name_ta", "உணவுப் பொருள்")
            score = float(result.get("freshness_score", 0.0))
            score = max(0.0, min(100.0, score))
            status = str(result.get("status", "SPOILED")).upper()
            conclusion = result.get(
                "conclusion_ta", "உணவுத் தரம் பரிசோதிக்கப்பட்டது."
            )
            recommendation = result.get(
                "recommendation_ta", "பாதுகாப்பான முறையில் கையாளவும்."
            )
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
