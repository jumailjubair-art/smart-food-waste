import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(
    page_title="AI Smart Food Waste & Donation System",
    page_icon="🍲",
    layout="centered"
)

st.title("🍲 AI Smart Food Waste & Donation System")
st.markdown("**பெஸ்ட் ப்ரோஸ் கூட்டணி** சார்பாக உணவுப் பொருள்களின் தரத்தை (Freshness) HSV கலர் மாஸ்கிங் மூலம் பகுப்பாய்வு செய்யும் தளம்! 🚀")
st.divider()

st.header("📸 உணவுப் படம் மற்றும் ஃபிரெஷ்னஸ் பரிசோதனை")
st.write("உணவுப் படத்தின் படத்தை இங்கே பதிவேற்றவும் (JPG/PNG)")

uploaded_file = st.file_uploader("Upload", type=["jpg", "jpeg", "png"])

def analyze_freshness(image):
    img_rgb = np.array(image.convert("RGB"))
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

    # 1. Fresh colourful foods mask (Green / Yellow / Orange / Warm tones)
    lower_fresh = np.array([25, 45, 50])
    upper_fresh = np.array([90, 255, 255])
    fresh_mask = cv2.inRange(hsv, lower_fresh, upper_fresh)

    # 2. Fresh white/cooked foods mask (Rice, Idli, Milk, Chapati - low saturation, good brightness)
    lower_white = np.array([0, 0, 130])
    upper_white = np.array([180, 75, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)

    combined_mask = cv2.bitwise_or(fresh_mask, white_mask)

    fresh_pixels = cv2.countNonZero(combined_mask)
    total_pixels = hsv.shape[0] * hsv.shape[1]

    if total_pixels == 0:
        return 0.0

    score = (fresh_pixels / total_pixels) * 100.0
    return round(min(100.0, max(0.0, score)), 2)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="பதிவேற்றப்பட்ட உணவுப் படம்", use_container_width=True)

    score = analyze_freshness(image)

    st.subheader("AI பகுப்பாய்வு முடிவு (Analysis)")
    st.markdown(f"🟢 **Freshness Score:** `{score:.2f}%`")

    if score >= 10.0:
        st.success("✅ **முடிவு: உணவு நல்ல நிலையில் (Fresh) உள்ளது!**")
        st.info("👉 **பரிந்துரை:** இந்த உணவை நல்ல முறையில் பயன்படுத்தலாம் அல்லது உணவு தான மையத்திற்கு (Food Donation) வழங்கலாம்! 🤝🍲")
    else:
        st.warning("⚠️ **முடிவு: உணவு கெட்டுப்போகும் நிலையில் உள்ளது அல்லது பழுத்துவிட்டது!**")
        st.info("👉 **பரிந்துரை:** மனித பயன்பாட்டிற்கு உகந்தது அல்ல. இதை உரம் தயாரிக்க (Composting) அனுப்பலாம்! 🌱")
else:
    st.info("💡 மேலே உள்ள பட்டனைப் பயன்படுத்தி ஒரு உணவுப் படத்தை அப்லோட் செய்யவும் ப்ரோ!")

st.divider()
st.caption("Developed with ❤️ by Best Bros (Jumail & AI)")
