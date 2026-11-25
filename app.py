import io
import json
import re
import time
import streamlit as st
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

DONATION_CONTACTS = [
    {
        "name_ta": "அருகிலுள்ள முதியோர் இல்லம் / ஆசரமம்",
        "area_ta": "உங்கள் சுற்றியுள்ள பகுதி",
        "phone": "நீங்களே நேரடியாகத் தேடி / விசாரித்து உறுதி செய்து கொள்ளவும்",
    },
    {
        "name_ta": "உணவு தானம் & ஆதரவற்றோர் இல்லம்",
        "area_ta": "உங்கள் சுற்றியுள்ள பகுதி",
        "phone": "நீங்களே நேரடியாகத் தேடி / விசாரித்து உறுதி செய்து கொள்ளவும்",
    },
]

def render_donation_section(highlight_fresh: bool = False):
    st.subheader("🤝 சுற்றியுள்ள தானம் & ஆசரமத் தொடர்புகள்")
    if highlight_fresh:
        st.success(
            "🍲 உணவு நல்ல தரத்தில் இருப்பதால், சுற்றியுள்ள ஆசரமம் அல்லது தான அமைப்புகளைத் "
            "தொடர்பு கொண்டு பாதுகாப்பாக வழங்கலாம்!"
        )
    else:
        st.caption(
            "உணவு தானம் தொடர்பான சுற்றியுள்ள தொடர்புத் தகவல்:"
        )

    for idx, item in enumerate(DONATION_CONTACTS, start=1):
        with st.container(border=True):
            st.markdown(f"**{idx}. {item['name_ta']}**")
            st.markdown(f"📍 **பகுதி:** `{item['area_ta']}`")
            st.markdown(f"📞 **தொடர்பு:** `{item['phone']}`")

def prepare_fast_image(uploaded_file) -> Image.Image:
    img = Image.open(uploaded_file).convert("RGB")
    max_size = 768
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75, optimize=True)
    buf.seek(0)
    return Image.open(buf)

@st.cache_resource
def get_genai_client(key: str):
    return genai.Client(api_key=key)

def contains_tamil(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))

def analyze_food_with_ai(image: Image.Image, key: str) -> dict:
    client = get_genai_client(key)
    prompt = (
        "CRITICAL LANGUAGE RULE: Write EVERY text field strictly in natural Tamil script (தமிழ்). "
        "Never use Hindi, Sanskrit, Telugu, Kannada, Malayalam, or English words in the values. "
        "For example, use 'புதியது' / 'நல்ல நிலையில் உள்ளது' instead of 'தாஜா'.\n"
        "First check whether the image shows an edible food item or drink. "
        "If the image is NOT food/drink (for example, it shows a human body part like hand/leg/face, a person, an animal, or a non-food object), "
        "set status to 'NOT_FOOD', freshness_score to 0, food_name_ta to 'உணவு அல்லாத படம்' (or specific non-food type in Tamil), "
        "conclusion_ta to clearly state that this is not a food item and cannot be checked as food freshness, "
        "and recommendation_ta to advise uploading a food item photo only.\n"
        "If it IS food/drink, carefully inspect for mold, fungus, discoloration, staleness, spoilage, or freshness. "
        "If mold, spots, decay, or spoilage is visible, give a low freshness_score (0 to 25) and status SPOILED; "
        "never mark spoiled or moldy food as FRESH or safe to donate.\n"
        "Return ONLY valid JSON:\n"
        '{"food_name_ta": "தமிழில் பொருளின் பெயர்", '
        '"freshness_score": 0 to 100 number, '
        '"status": "FRESH" or "MODERATE" or "SPOILED" or "NOT_FOOD", '
        '"conclusion_ta": "தமிழில் சுருக்கமான முடிவு", '
        '"recommendation_ta": "தானம் அல்லது உடனடி பயன்பாடு அல்லது உரம் அல்லது உணவுப் படம் பதிவேற்றும் தமிழ் பரிந்துரை"}'
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

st.header("📸 உணவுப் படம் மற்றும் AI ஃபிரெஷ்னஸ் பரிசோதனை")
st.write("உணவுப் பொருளின் படத்தை இங்கே பதிவேற்றவும் (JPG/PNG)")

uploaded_file = st.file_uploader("Upload", type=["jpg", "jpeg", "png"])

def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return st.session_state.get("temp_gemini_api_key", "")

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
    if not api_key:
        st.error(
            "⚠️ **GEMINI_API_KEY கிடைக்கவில்லை!** Streamlit Secrets-ல் `GEMINI_API_KEY` "
            "சேர்க்கவும் அல்லது மேலே உள்ள 'Gemini API Key அமைப்பு' பகுதியில் தற்காலிகமாக உள்ளிடவும்."
        )
    else:
        cache_key = f"{uploaded_file.name}_{uploaded_file.size}_ta_v21"
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
            status = str(result.get("status", "SPOILED")).upper()
            conclusion = result.get(
                "conclusion_ta", "உணவுத் தரம் பரிசோதிக்கப்பட்டது."
            )
            recommendation = result.get(
                "recommendation_ta", "பாதுகாப்பான முறையில் கையாளவும்."
            )
            st.subheader("🤖 AI பகுப்பாய்வு முடிவு (Gemini Vision)")
            if status == 'NOT_FOOD':
                st.markdown(f"🚫 **படம் வகை:** `{food_name}`")
                st.warning(f"⚠️ **கவனம்:** {conclusion}")
                st.info(f"👉 **பரிந்துரை:** {recommendation}")
                st.divider()
                render_donation_section(highlight_fresh=False)
            else:
                score = float(result.get("freshness_score", 0.0))
                score = max(0.0, min(100.0, score))
                if status == 'SPOILED' and score > 30.0:
                    score = 18.0
                elif status == 'MODERATE' and (score < 30.0 or score >= 60.0):
                    score = 45.0
                elif status == 'FRESH' and score < 60.0:
                    score = 78.0
                st.markdown(f"🍽️ **அடையாளம் காணப்பட்ட பொருள்:** `{food_name}`")
                st.markdown(f"📊 **AI Freshness Score:** `{score:.1f}%`")
                is_fresh = status == 'FRESH' and score >= 60.0
                if is_fresh:
                    st.success(f"✅ **முடிவு:** {conclusion}")
                    st.info(f"👉 **பரிந்துரை:** {recommendation} 🤝🍲")
                elif status == 'MODERATE' or (30.0 <= score < 60.0):
                    st.warning(f"⚠️ **முடிவு:** {conclusion}")
                    st.info(f"👉 **பரிந்துரை:** {recommendation}")
                else:
                    st.error(f"⚠️ **முடிவு:** {conclusion}")
                    st.info(f"👉 **பரிந்துரை:** {recommendation} 🌱")
                st.divider()
                render_donation_section(highlight_fresh=is_fresh)
else:
    st.info("💡 மேலே உள்ள பட்டனைப் பயன்படுத்தி ஒரு உணவுப் படத்தை அப்லோட் செய்யவும் ப்ரோ!")
    st.divider()
    render_donation_section(highlight_fresh=False)

st.divider()
st.caption("Developed with ❤️ by Best Bros (Jumail & AI)")
