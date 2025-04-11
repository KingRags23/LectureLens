import streamlit as st
import requests
import time
import os

# 🔐 API Keys
MAVI_API_KEY = "sk-ee4b6a75cdf23516463969c65fe71ab9"
GEMINI_API_KEY = "AIzaSyAbGbaVPBR_2L3NzxAPWmIf2iwquZvv7yA"

# 🔗 Endpoints
MAVI_UPLOAD_URL = "https://mavi-backend.openinterx.com/api/serve/video/upload"
MAVI_SEARCH_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchDB"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

st.set_page_config("SmartLecture", layout="wide")
st.title("🎓 SmartLecture – Real-Time Confusion Helper")


st.subheader("📥 Step 1: Upload Your Lecture Video")

uploaded_file = st.file_uploader("Upload a video", type=["mp4", "mov", "mkv"])

if uploaded_file:
    temp_filename = f"temp_{uploaded_file.name}"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_file.read())

    st.video(temp_filename)
    st.success("✅ Video uploaded locally")

    if st.button("📡 Send to MAVI"):
        st.info("Sending video to MAVI...")
        with open(temp_filename, "rb") as video_file:
            files = {
                "file": (uploaded_file.name, video_file, "video/mp4")
            }
            headers = {
                "Authorization": f"Bearer {MAVI_API_KEY}"
            }
            response = requests.post(MAVI_UPLOAD_URL, headers=headers, files=files)

        result = response.json()
        if response.status_code == 200 and "data" in result:
            video_no = result["data"]["videoNo"]
            st.session_state.video_no = video_no
            st.session_state.video_name = uploaded_file.name
            st.success(f"✅ Uploaded to MAVI! Video No: `{video_no}`")
        else:
            st.error("❌ Upload failed.")
            st.json(result)

# -----------------------------
# ⏳ Poll MAVI for Status
# -----------------------------
if "video_no" in st.session_state:
    st.subheader("⏳ Step 2: Check When MAVI Is Done Processing")

    if st.button("🔁 Poll MAVI for 'PARSE' status"):
        with st.spinner("Polling MAVI every 5 seconds (max 1 min)..."):
            found = False
            for _ in range(12):
                params = {"videoNo": st.session_state.video_no}
                headers = {"Authorization": f"Bearer {MAVI_API_KEY}"}
                resp = requests.get(MAVI_SEARCH_URL, headers=headers, params=params)
                data = resp.json()

                if (
                    "data" in data
                    and "videos" in data["data"]
                    and len(data["data"]["videos"]) > 0
                    and data["data"]["videos"][0]["videoStatus"] == "PARSE"
                ):
                    found = True
                    break
                time.sleep(5)

            if found:
                st.success("✅ MAVI finished processing!")
                st.session_state.parsed = True
            else:
                st.warning("⚠️ MAVI has not finished parsing yet. Try again later.")

# -----------------------------
# 🧠 Generate Summary via Gemini
# -----------------------------
if st.session_state.get("parsed", False):
    st.subheader("🧠 Step 3: Auto-Generate Summary with Gemini")

    default_prompt = f"""
    The video titled "{st.session_state.video_name}" is a lecture. 
    Generate a brief summary and 3 highlight moments with timestamps based on its expected content.
    Pretend you’ve watched it.
    """
    st.markdown("✍️ You can edit the Gemini prompt below:")
    custom_prompt = st.text_area("Gemini Summary Prompt", value=default_prompt, height=150)

    if st.button("🧠 Generate Summary"):
        body = {
            "contents": [{"parts": [{"text": custom_prompt}]}]
        }
        headers = {"Content-Type": "application/json"}
        params = {"key": GEMINI_API_KEY}

        with st.spinner("Calling Gemini..."):
            chat_resp = requests.post(GEMINI_URL, headers=headers, params=params, json=body)
            chat_data = chat_resp.json()

            try:
                text = chat_data["candidates"][0]["content"]["parts"][0]["text"]
                st.session_state.gemini_summary = text
                st.success("✅ Gemini summary generated!")
            except Exception as e:
                st.error("❌ Gemini did not return a valid response.")
                st.json(chat_data)

# -----------------------------
# 📝 Show Gemini Summary Output
# -----------------------------
if "gemini_summary" in st.session_state:
    st.subheader("📄 Gemini Summary")
    st.markdown(st.session_state.gemini_summary)

# -----------------------------
# 💬 Gemini Chatbot
# -----------------------------
    st.subheader("💬 Ask Gemini About the Video")

    user_question = st.text_input("Ask something based on the lecture content")

    if user_question:
        prompt = f"""
        Context: {st.session_state.gemini_summary}
        Question: {user_question}
        Please answer like a helpful tutor based on the above summary.
        """
        body = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        headers = {"Content-Type": "application/json"}
        params = {"key": GEMINI_API_KEY}

        with st.spinner("Thinking with Gemini..."):
            chat_resp = requests.post(GEMINI_URL, headers=headers, params=params, json=body)
            chat_data = chat_resp.json()

            try:
                answer = chat_data["candidates"][0]["content"]["parts"][0]["text"]
                st.markdown(f"🧠 **Gemini:** {answer}")
            except Exception as e:
                st.error("❌ Gemini did not return a valid answer.")
                st.json(chat_data)
