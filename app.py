import base64
import io
from datetime import datetime
import os

import streamlit as st
from PIL import Image
from streamlit_javascript import st_javascript
import openai

# ---------- App config (must be near the top) ----------
st.set_page_config(page_title="Green Building Materials Advisor", layout="wide")


# ---------- Helpers ----------
def get_api_key() -> str | None:
    """
    Securely load the OpenAI API key.
    Priority:
      1) st.secrets["openai"]["api_key"]  (Streamlit Cloud Secrets)
      2) environment variable OPENAI_API_KEY
      3) optional user input in the sidebar (handled outside)
    """
    # 1) Streamlit secrets
    try:
        key = st.secrets["openai"]["api_key"]
        if key:
            return key
    except Exception:
        pass

    # 2) Environment variable
    return os.getenv("OPENAI_API_KEY")


def encode_image_to_base64(image: Image.Image) -> str:
    """Convert a PIL Image to a base64 string (JPEG, resized if large)."""
    max_size = (1024, 1024)
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str


def analyze_building_with_gpt4o(image_base64: str, api_key: str, budget: str, ai_style: str) -> str | None:
    """Send image + instructions to OpenAI GPT-4o and return the text answer."""
    try:
        client = openai.OpenAI(api_key=api_key)

        prompt = f"""
You are a green building materials expert.

1) The user provides an image (blueprint or photo) of a building they plan to build or improve.
2) Recommend the best materials to build/upgrade this structure with a sustainability focus.
3) Adjust choices to the user's customization and needs: The user's budget level is {budget} and your tone should be {ai_style}.
4) Provide specific, actionable recommendations with brief explanations (durability, embodied carbon, insulation value, maintenance, cost tradeoffs).
5) Where helpful, suggest alternatives by budget tier and note key standards/certifications (e.g., FSC, EPD, Energy Star).

When you are ready, begin your report with the following:

Hi {name}, 
"""

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=2000,
            temperature=0.7,
        )

        return resp.choices[0].message.content

    except openai.AuthenticationError:
        st.error("Authentication failed. Please check your OpenAI API key.")
    except openai.RateLimitError:
        st.error("Rate limit exceeded. Please try again later.")
    except openai.APIError as e:
        st.error(f"API error occurred: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

    return None


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<h3 class="sub-header">🔧 Configuration</h3>', unsafe_allow_html=True)

    # Optional manual override for the key
    user_api_key = st.text_input(
        "OpenAI API Key (optional override)",
        type="password",
        help="If left blank, the app will use Streamlit Secrets or the OPENAI_API_KEY environment variable.",
    )

    resolved_api_key = user_api_key or get_api_key()

    if resolved_api_key:
        st.success("✅ API key configured")
        if user_api_key:
            st.info("Using the manually entered API key.")
        else:
            st.info("Using Streamlit Secrets or environment variable.")
    else:
        st.error("❌ No API key found.")
        st.info("Set it in Streamlit Secrets as openai.api_key or as environment variable OPENAI_API_KEY.")

    st.markdown("---")
    st.markdown("### 📋 How to Use")
    st.markdown(
        "1. Ensure an OpenAI API key is set\n"
        "2. Upload an image of your building/blueprint\n"
        "3. Choose budget and response style\n"
        "4. Click **Submit** to get recommendations"
    )
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown(
        "This app uses OpenAI GPT-4o to analyze your building image and suggest more sustainable material choices."
    )


# ---------- Main UI ----------
# Detect browser hour for greeting
hour = st_javascript("new Date().getHours()") or datetime.utcnow().hour
daytime = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

st.markdown(
    f"""
    <div style="background-image: url('https://images.pexels.com/photos/4322027/pexels-photo-4322027.jpeg');
                padding: 2.5rem; text-align: center; background-size: cover; border-radius: 10px;">
        <h1 style="color: white; text-shadow: 1px 1px 2px black;">Good {daytime}, my friend!</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br><hr><br>", unsafe_allow_html=True)

col2, col3, col4, col5, col6, space, col7 = st.columns([2, 1, 2, 1, 2, 1, 2])

with col2:
    st.markdown(
        """
        <h5>ℹ️ Instructions:</h5>
        <ul style="line-height: 1.6;">
            <li><strong>Upload your full-view building image</strong> in the middle column.</li>
            <li><strong>Fill in preferences</strong> in the third column.</li>
            <li>Click <strong>Submit</strong> to get green building tips.</li>
        </ul>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown("<h5>📤 Upload Your File</h5>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Choose an image file", type=["png", "jpg", "jpeg"], help="Upload a clear photo or blueprint."
    )
    image = None
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)

with col6:

    st.markdown("<div style='font-size: 1.1rem;'>👤 <strong>Your Name</strong></div>", unsafe_allow_html=True)
    name = st.text_input(" ", label_visibility="collapsed")
    
    st.markdown("<div style='font-size: 1.1rem;'>💵 <strong>Budget Level</strong></div>", unsafe_allow_html=True)
    budget = st.selectbox(" ", ["Basic", "Standard", "Premium"], label_visibility="collapsed")

    st.markdown("<div style='font-size: 1.1rem;'>🤖 <strong>AI Response Style</strong></div>", unsafe_allow_html=True)
    ai_style = st.selectbox(" ", ["Casual", "Formal", "Informative", "Normal"], label_visibility="collapsed")

    if st.button("🚀 Submit", type="primary", use_container_width=True):
        if not resolved_api_key:
            st.error("❌ No API key configured.")
        elif image is None:
            st.error("Please upload an image before submitting.")
        else:
            with st.spinner("Analyzing your building..."):
                image_base64 = encode_image_to_base64(image)
                result = analyze_building_with_gpt4o(image_base64, resolved_api_key, budget, ai_style)
                if result:
                    st.session_state.analysis_result = result
                    st.success("Analysis complete! See the results on the bottom.")
                else:
                    st.error("Failed to analyze the image. Please try again.")

with col7:
    st.markdown('<h3 class="sub-header">📊 Analysis Results</h3>', unsafe_allow_html=True)
    if "analysis_result" in st.session_state:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("### 🧱 Building Material Recommendations")
        st.markdown(st.session_state.analysis_result)
        st.markdown("</div>", unsafe_allow_html=True)

        st.download_button(
            label="📥 Download Analysis Report",
            data=st.session_state.analysis_result,
            file_name="green_building_analysis.txt",
            mime="text/plain",
        )
    else:
        st.info("Upload a photo and click 'Analyze Building' to see recommendations here.")
