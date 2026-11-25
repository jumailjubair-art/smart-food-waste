import cv2
import numpy as np
from PIL import Image
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Smart Food Waste & Donation System", page_icon="🍲", layout="centered"
)

# App Title & UI Header
st.title("🍲 AI Smart Food Waste & Donation System")
st.markdown(
    "**பெஸ்ட் ப்ரோஸ் கூட்டணி** சார்பாக உணவுப் பொருள்களின் தரத்தை (Freshness) HSV கலர் மாஸ்கிங் மூலம் பகுப்பாய்வு செய்யும் தளம்! 🚀"
)
st.markdown("---")

# Sidebar - Mode Selection
st.sidebar.header("⚙️ மெனு (Menu)")
app_mode = st.sidebar.selectbox(
    "செயல்பாட்டைத் தேர்ந்தெடுக்கவும்:",
    ["உணவுப் பரிசோதனை (Food Analysis)", "தானம் / உரம் (Donation / Composting)"],
)

if app_mode == "உணவுப் பரிசோதனை (Food Analysis)":
  st.header("📸 உணவுப் படம் மற்றும் ஃபிரெஷ்னெஸ் பரிசோதனை")

  # Image Upload Option
  uploaded_file = st.file_uploader(
      "உணவுப் படத்தின் படத்தை இங்கே பதிவேற்றவும் (JPG/PNG)", type=["jpg", "jpeg", "png"]
  )

  if uploaded_file is not None:
    # Load Image
    image = Image.open(uploaded_file)
    image_np = np.array(image)

    col1, col2 = st.columns(2)

    with col1:
      st.subheader("பதிவேற்றிய உணவு")
      st.image(image, use_column_width=True)

    with col2:
      st.subheader("AI பகுப்பாய்வு முடிவு (Analysis)")

      # Convert RGB to HSV for color masking analysis
      hsv = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)

      # Lower and Upper Green range for fresh food
      lower_green = np.array([35, 40, 40])
      upper_green = np.array([85, 255, 255])

      mask = cv2.inRange(hsv, lower_green, upper_green)
      green_pixel_count = np.count_nonzero(mask)
      total_pixels = mask.size
      green_percentage = (green_pixel_count / total_pixels) * 100

      st.write(f"🟢 **Freshness Score:** {green_percentage:.2f}%")

      # Decision Logic
      if green_percentage > 15:
        st.success(
            "✅ **முடிவு:** உணவு நல்ல தரத்திலுள்ளது! (Safe for Donation)"
        )
        st.markdown(
            "👉 **பரிந்துரை:** இந்த உணவை உடனடியாக அருகில் உள்ள ஏழை எளியோருக்கு"
            " அல்லது உணவு வங்கிக்கு (Food Bank) தானம் செய்யலாம்! 🤝"
        )
      else:
        st.warning("⚠️ **முடிவு:** உணவு கெட்டுப்போகும் நிலையில் உள்ளது அல்லது பழுத்துவிட்டது!")
        st.markdown(
            "👉 **பரிந்துரை:** மனித பயன்பாட்டிற்கு உகந்தது அல்ல. இதை உரம் தயாரிக்க"
            " (Composting) அனுப்பலாம்! 🌱"
        )

  else:
    st.info("💡 மேலே உள்ள பட்டனைப் பயன்படுத்தி ஒரு உணவுப் படத்தை அப்லோட் செய்யவும் ப்ரோ!")

elif app_mode == "தானம் / உரம் (Donation / Composting)":
  st.header("📍 அருகில் உள்ள மையங்கள் மற்றும் வழிகாட்டுதல்கள்")
  st.markdown(
      "இந்தப்பிரிவு மூலம் நீங்கள் சேகரித்த உணவை சரியான முறையில் இடமாற்றம் செய்ய"
      " முடியும்."
  )

  col1, col2 = st.columns(2)
  with col1:
    st.info("🤝 **உணவு தானப் பிரிவு (Food Donation)**\n\n- அருகில் உள்ள NGOs\n- உணவு வங்கி முகவரிகள்")
  with col2:
    st.success(
        "🌱 **உரம் தயாரிப்பு (Composting Guide)**\n\n- மக்கும் குப்பை மேலாண்மை\n- தாவர"
        " உரம் தயாரிப்பு முறை"
    )

# Footer
st.markdown("---")
st.markdown(
    "<center><b>Developed with ❤️ by Best Bros (Jumail & AI)</b></center>",
    unsafe_allow_html=True,
)
