import os
import json
import random
import datetime
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

# Page Configuration
st.set_page_config(
    page_title="Juju - AI Smart Food Waste & Donation System",
    page_icon="🍊",
    layout="centered"
)

# Custom CSS for clean mobile-friendly UI
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 0.5rem 0 1rem 0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='main-header'><h1>🍊 Juju Food Donation & Freshness AI</h1><p>உணவு ஃபிரெஷ்னஸ் பரிசோதனை & எளிய உணவு தானத் திட்டம்</p></div>", unsafe_allow_html=True)

# Initialize session state for donation records
if "juju_donations" not in st.session_state:
    st.session_state["juju_donations"] = []

# API Key Setup (supports Streamlit Secrets or Environment Variable)
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

with st.sidebar:
    st.header("⚙️ Juju அமைப்புகள்")
    if not api_key:
        manual_key = st.text_input("Gemini API Key உள்ளிடவும்", type="password", placeholder="AIza...")
        if manual_key:
            api_key = manual_key
    else:
        st.success("✅ Gemini AI இணைக்கப்பட்டுள்ளது")
    st.info("🏢 **நிறுவனம்:** Juju Food Donation\n\nஉணவை வீணாக்காமல் பகிர்வோம்!")


def analyze_food_with_ai(pil_image: Image.Image, key: str) -> dict:
    """
    Analyzes food freshness using google-genai (Gemini Vision) with strict spoilage detection.
    """
    client = genai.Client(api_key=key)
    prompt = """
    You are an expert food safety and quality inspector for 'Juju', a food donation organization.
    Carefully inspect the uploaded food image for any signs of spoilage, mold (white, green, black, fuzzy spots),
    discoloration, sliminess, rotting, bruising, stale/dry appearance, or unsafe conditions.

    STRICT RULES:
    1. If there is ANY visible mold, rot, dark spoilage spots, or signs the food is spoiled/stale,
       you MUST classify status as "SPOILED" and give a freshness_score BELOW 40 (e.g., 10 to 35).
       NEVER mark spoiled or moldy bread/food as FRESH.
    2. Only classify status as "FRESH" with freshness_score >= 60 if the food looks clean, safe, intact, and edible for human donation.
    3. If lighting is unclear or borderline, give a cautious score between 45 and 59 and status "UNCERTAIN".

    Respond ONLY with valid JSON in this exact structure:
    {
        "food_name_tamil": "உணவின் பெயர் தமிழில் (எ.கா. பிரெட் / சாதம் / பழங்கள்)",
        "status": "FRESH" or "SPOILED" or "UNCERTAIN",
        "freshness_score": 0 to 100 integer,
        "observation_tamil": "படத்தில் காணப்படும் தரம் குறித்த சுருக்கமான விளக்கம் தமிழில்"
    }
    """

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[pil_image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    return json.loads(response.text)


def render_donation_scheme(status: str, freshness_score: int, food_label: str):
    """
    Renders the Juju Food Donation Scheme form and token generator for FRESH food.
    """
    st.markdown("---")
    st.subheader("🤝 ஜூஜூ (Juju) உணவு தானத் திட்டம்")
    st.success(
        f"✅ **தானத்திற்குத் தகுதியானது!** ({food_label} • ஃப்ரெஷ்னஸ் ஸ்கோர்: {freshness_score}%) — "
        "கீழே உள்ள எளிய படிவத்தை நிரப்பி உடனே தானப் பதிவை உருவாக்கலாம்."
    )

    with st.form("juju_donation_form", clear_on_submit=True):
        donor_name = st.text_input("உங்கள் பெயர் *", placeholder="எ.கா. ஜுமைல் / ஜூஜூ தன்னார்வலர்")
        col1, col2 = st.columns(2)
        with col1:
            food_type = st.selectbox(
                "உணவு வகை *",
                [
                    "சமைத்த உணவு / மதிய உணவு",
                    "பழங்கள் & காய்கறிகள்",
                    "பிரெட் / பேக்கரி பொருட்கள்",
                    "அரிசி / பருப்பு / பாக்கெட் உணவு",
                ],
            )
        with col2:
            quantity = st.text_input("அளவு (எ.கா. 5 பாக்கெட் / 3 kg) *", placeholder="எ.கா. 10 Meals")

        pickup_window = st.selectbox(
            "எப்போது எடுக்கலாம்? (Pickup Window) *",
            ["இப்போதே (30 நிமிடத்திற்குள்)", "1 மணி நேரத்திற்குள்", "இன்று மாலைக்குள்"],
        )
        location = st.text_input("இடம் / முகவரி *", placeholder="எ.கா. ராஜபாளையம் மெயின் ரோடு")
        recipient_hub = st.selectbox(
            "யாருக்கு அனுப்ப விரும்புகிறீர்கள்?",
            [
                "அருகிலுள்ள ஆசரமம் (Local Ashram)",
                "ஜூஜூ சமுதாய உணவு மையம்",
                "தெருவோரத் தேவைப்படுவோர்",
            ],
        )
        notes = st.text_area("கூடுதல் குறிப்பு (விரும்பினால்)", placeholder="சூடாக உள்ளது, வெஜ் மட்டும் போன்ற குறிப்புகள்...")

        submitted = st.form_submit_button("🎁 தானப் பதிவை உறுதி செய் (Generate Token)")

    if submitted:
        if not donor_name.strip() or not quantity.strip() or not location.strip():
            st.error("தயவுசெய்து **பெயர்**, **அளவு**, மற்றும் **இடம்** ஆகியவற்றை நிரப்பவும்.")
        else:
            token_id = f"JUJU-{datetime.datetime.now().strftime('%H%M')}-{random.randint(100, 999)}"
            record = {
                "Token": token_id,
                "Donor": donor_name.strip(),
                "Food": f"{food_label} ({food_type})",
                "Quantity": quantity.strip(),
                "Pickup": pickup_window,
                "Location": location.strip(),
                "Hub": recipient_hub,
                "Score": f"{freshness_score}%",
                "Notes": notes.strip() or "-",
            }
            st.session_state["juju_donations"].insert(0, record)

            st.balloons()
            st.info(
                f"🎉 **தானப் பதிவு வெற்றிகரமாக உருவாக்கப்பட்டது!**\n\n"
                f"- **டோக்கன் எண்:** `{token_id}`\n"
                f"- **தானம் செய்பவர்:** {record['Donor']}\n"
                f"- **உணவு & அளவு:** {record['Food']} - {record['Quantity']}\n"
                f"- **பிக்-அப் நேரம்:** {record['Pickup']}\n"
                f"- **இடம்:** {record['Location']}\n"
                f"- **மையம்:** {record['Hub']}"
            )


def render_compost_contacts(food_label: str, freshness_score: int, status: str):
    """
    Renders Compost & Waste-to-Resource contacts when food is SPOILED or below 60% score.
    """
    st.markdown("---")
    if status == "SPOILED":
        st.error(
            f"🚫 **{food_label}** தற்போதைய AI பரிசோதனையில் **SPOILED** ({freshness_score}%) என வந்துள்ளது. "
            "உடல்நலப் பாதுகாப்புக்காக இதை மனிதர்களுக்கு தானம் செய்ய வேண்டாம்; உரமாக்க அல்லது கழிவு மேலாண்மை மையத்தில் ஒப்படைக்கவும்."
        )
    else:
        st.warning(
            f"⚠️ **{food_label}** ஸ்கோர் குறைவாக ({freshness_score}%) உள்ளது. "
            "நேரில் நிறம்/வாசனையைப் பரிசோதிக்கவும்; சந்தேகம் இருந்தால் தானம் செய்யாமல் கீழே உள்ள உர மையங்களுக்கு அனுப்பவும்."
        )

    st.subheader("🌱 உரமாக்கல் & கழிவு மேலாண்மைத் தொடர்புகள் (Compost Contacts)")
    st.caption(
        "குறிப்பு: கீழே உள்ள தொடர்பு விவரங்கள் மாதிரி/டெம்ப்ளேட் வடிவில் உள்ளன. "
        "உங்கள் பகுதி நகராட்சி / உர மையத்தின் உண்மையான எண்ணையும் முகவரியையும் இங்கே சேர்த்துக் கொள்ளலாம்."
    )

    compost_partners = [
        {
            "மையம் / சேவை": "உள்ளூர் நகராட்சி மக்கும் குப்பை உர மையம் (MCC)",
            "வகை": "Municipal Composting",
            "தொடர்பு நபர் / பிரிவு": "சுகாதாரம் & திடக்கழிவு மேலாண்மைப் பிரிவு",
            "போன் எண்": "+91 98765 43210",
            "முகவரி": "நகராட்சி மக்கும் கழிவு மையம், ராஜபாளையம்",
            "குறிப்பு": "காய்கறி, பழம் மற்றும் சமையலறை மக்கும் கழிவுகளை உரமாக்க ஏற்கப்படும்.",
        },
        {
            "மையம் / சேவை": "ஜூஜூ பசுமை உரம் & பயோ-கம்போஸ்ட் யூனிட்",
            "வகை": "Organic Compost Partner",
            "தொடர்பு நபர் / பிரிவு": "Compost Collection Coordinator",
            "போன் எண்": "+91 98765 43211",
            "முகவரி": "பசுமை உரத் தளம், மெயின் ரோடு, ராஜபாளையம்",
            "குறிப்பு": "கெட்டுப்போன தாவர/உணவுப் பொருட்களை பாதுகாப்பான உரமாக மாற்ற வழிகாட்டும்.",
        },
        {
            "மையம் / சேவை": "பண்ணை / கால்நடை உரக் குழி (Farm Pit Compost)",
            "வகை": "Local Farm / Soil Compost",
            "தொடர்பு நபர் / பிரிவு": "விவசாய / உர ஒருங்கிணைப்பாளர்",
            "போன் எண்": "+91 98765 43212",
            "முகவரி": "அருகிலுள்ள விவசாய நிலம் / கம்போஸ்ட் குழி",
            "குறிப்பு": "மண்ணில் புதைத்து இயற்கை உரமாக்க (பூஞ்சை பிடித்தவற்றை கவனமாகப் பார்க்கவும்).",
        },
    ]

    for partner in compost_partners:
        with st.container(border=True):
            st.markdown(f"**{partner['மையம் / சேவை']}** (`{partner['வகை']}`)")
            st.write(f"👤 **தொடர்பு:** {partner['தொடர்பு நபர் / பிரிவு']}")
            st.write(f"📞 **போன்:** `{partner['போன் எண்']}`")
            st.write(f"📍 **இடம்:** {partner['முகவரி']}")
            st.write(f"📝 **குறிப்பு:** {partner['குறிப்பு']}")
            st.markdown(f"[📲 இப்போது அழைக்கவும் (Call)](tel:{partner['போன் எண்'].replace(' ', '')})")


# --- MAIN CAMERA & UPLOAD SECTION ---
st.subheader("📷 ஃபிரெஷ்னஸ் பரிசோதனை")

# Live Phone Camera Input
camera_photo = st.camera_input("உணவுப் பொருளை கேமராவில் காட்டிப் படம் எடுக்கவும்")

# Gallery Upload Option as Backup
gallery_photo = st.file_uploader(
    "அல்லது கேலரியில் இருந்து உணவுப் படத்தை பதிவேற்றவும் (JPG/PNG)",
    type=["jpg", "jpeg", "png"],
)

# Mandatory bright photo note right below the upload/camera box
st.caption("📸 **Must take a bright photo** — நல்ல வெளிச்சத்தில் தெளிவாகப் படம் எடுக்கவும் (நிழல் அல்லது இருட்டு படங்களைத் தவிர்க்கவும்).")

captured_image = camera_photo if camera_photo is not None else gallery_photo

if captured_image is not None:
    pil_img = Image.open(captured_image).convert("RGB")
    st.image(pil_img, caption="பரிசோதனைக்குத் தேர்ந்தெடுக்கப்பட்ட உணவுப் படம்", use_container_width=True)

    if not api_key:
        st.error("⚠️ இடதுபுற சைட்பாரில் (Sidebar) அல்லது Streamlit Secrets-ல் `GEMINI_API_KEY` சேர்க்கவும்.")
    else:
        with st.spinner("🤖 Juju AI உணவின் தரத்தை ஆராய்கிறது..."):
            try:
                result = analyze_food_with_ai(pil_img, api_key)
                food_label = result.get("food_name_tamil", "உணவுப் பொருள்")
                status = str(result.get("status", "UNCERTAIN")).upper()
                score = int(result.get("freshness_score", 0))
                observation = result.get("observation_tamil", "")

                st.markdown("### 📊 பரிசோதனை முடிவு")
                col_a, col_b = st.columns(2)
                col_a.metric("உணவு நிலை (Status)", status)
                col_b.metric("ஃப்ரெஷ்னஸ் ஸ்கோர்", f"{score}%")
                st.write(f"**உணவு:** {food_label}")
                if observation:
                    st.write(f"**AI கவனிப்பு:** {observation}")

                # Route based on freshness status & 60% safety threshold
                if status == "FRESH" and score >= 60:
                    render_donation_scheme(status, score, food_label)
                else:
                    render_compost_contacts(food_label, score, status)

            except Exception as e:
                st.error(f"AI பரிசோதனையில் பிழை ஏற்பட்டது: {e}")
else:
    st.info("💡 மேலே உள்ள கேமரா அல்லது அப்லோட் பட்டனைப் பயன்படுத்தி ஒரு உணவுப் படத்தை எடுக்கவும் ப்ரோ!")

# Display today's donation records if any exist
if st.session_state["juju_donations"]:
    st.markdown("---")
    st.markdown("### 📋 இன்றைய Juju தானப் பதிவுகள்")
    st.dataframe(st.session_state["juju_donations"], use_container_width=True)
