import json
import time
import urllib.parse
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

# அருகிலுள்ள ஆசரமம் / தானம் தொடர்புப் பட்டியல் (உங்கள் பகுதிக்கு ஏற்ப மாற்றிக் கொள்ளலாம்)
DONATION_CONTACTS = [
    {
        "name_ta": "அருகிலுள்ள முதியோர் இல்லம் / ஆசரமம் (மாதிரி)",
        "area_ta": "உங்கள் பகுதி / அருகிலுள்ள நகரம்",
        "phone": "உங்கள் தொடர்பு எண்ணை இங்கே சேர்க்கவும்",
        "map_query": "Ashram old age home food donation near me",
    },
    {
        "name_ta": "உணவு தானம் & ஆதரவற்றோர் இல்லம் (மாதிரி)",
        "area_ta": "உங்கள் பகுதி / அருகிலுள்ள நகரம்",
        "phone": "உங்கள் தொடர்பு எண்ணை இங்கே சேர்க்கவும்",
        "map_query": "Orphanage food bank donation near me",
    },
]


def render_donation_section(highlight_fresh: bool = False):
    st.subheader("🤝 அருகிலுள்ள ஆசரமம் & உணவு தானத் தொடர்புகள்")
    if highlight_fresh:
        st.success(
            "🍲 உணவு நல்ல தரத்தில் இருப்பதால், அருகிலுள்ள ஆசரமம் அல்லது தான அமைப்புகளைத் "
            "தொடர்பு கொண்டு பாதுகாப்பாக வழங்கலாம்!"
        )
    else:
        st.caption(
            "உணவு தானம் தொடர்பான விரைவுத் தகவல் மற்றும் Google Maps தேடல் இணைப்புகள்:"
        )

    for idx, item in enumerate(DONATION_CONTACTS, start=1):
        encoded_q = urllib.parse.quote_plus(item["map_query"])
        maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_q}"
        with st.container(border=True):
            st.markdown(f"**{idx}. {item['name_ta']}**")
            st.markdown(f"📍 **பகுதி:** `{item['area_ta']}`")
            st.markdown(f"📞 **தொடர்பு எண்:** `{item['phone']}`")
            st.markdown(f"🗺️ [Google Maps-ல் அருகிலுள்ள இடங்களைத் தேடவும்]({maps_url})")


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


def analyze_food_with_ai(image: Image.Image, key: str) -> dict:
    client = genai.Client(api_key=key)

    prompt = (
        "You are a food quality and safety AI assistant. Analyze the uploaded image. "
        "1. Identify what food item (or non-food item) is shown. "
        "2. Evaluate its freshness without relying on green color pixels alone—inspect texture, "
        "spoilage signs, mold, discoloration, wilting, or curdling/drying. "
        "3. Return ONLY valid JSON with these exact keys: "
        '{"food_name_ta": "தமிழில் உணவுப் பெயர்", '
        '"freshness_score": 0 to 100 number, '
        '"status": "FRESH" or "MODERATE" or "SPOILED", '
        '"conclusion_ta": "தமிழில் சுருக்கமான முடிவு", '
        '"recommendation_ta": "தானம் (Food Donation) அல்லது உடனடி பயன்பாடு அல்லது உரம் (Composting) பற்றிய தமிழில் பரிந்துரை"}'
    )

    models_to_try = ["gemini-3.8-flash", "gemini-flash-latest"]
    last_error = None

    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[image, prompt],
                    config={"response_mime_type": "application/json"},
                )
                raw_text = (response.text or "").strip()
                return json.loads(raw_text)
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break

    raise last_error if last_error else RuntimeError("AI analysis failed")


if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="பதிவேற்றப்பட்ட உணவுப் படம்", use_container_width=True)

    if not api_key:
        st.error(
            "⚠️ **GEMINI_API_KEY கிடைக்கவில்லை!** Streamlit Secrets-ல் `GEMINI_API_KEY` "
            "சேர்க்கவும் அல்லது மேலே உள்ள 'Gemini API Key அமைப்பு' பகுதியில் தற்காலிகமாக உள்ளிடவும்."
        )
    else:
        with st.spinner("🤖 Gemini AI உணவுப் படத்தை அடையாளம் கண்டு பகுப்பாய்வு செய்கிறது..."):
            try:
                result = analyze_food_with_ai(image, api_key)

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
                render_donation_section(highlight_fresh=is_fresh)

            except Exception as e:
                st.error(f"❌ AI பகுப்பாய்வில் பிழை ஏற்பட்டது: {e}")
else:
    st.info("💡 மேலே உள்ள பட்டனைப் பயன்படுத்தி ஒரு உணவுப் படத்தை அப்லோட் செய்யவும் ப்ரோ!")
    st.divider()
    render_donation_section(highlight_fresh=False)

st.divider()
st.caption("Developed with ❤️ by Best Bros (Jumail & AI)")
