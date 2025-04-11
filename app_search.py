import streamlit as st
import requests
import os

# 🔐 API Keys
MAVI_API_KEY = "sk-7cd38706a5e62c9da49f8014ad69d346"
GEMINI_API_KEY = "AIzaSyAbGbaVPBR_2L3NzxAPWmIf2iwquZvv7yA"

# 🔗 Endpoints
MAVI_UPLOAD_URL = "https://mavi-backend.openinterx.com/api/serve/video/upload"
MAVI_SEARCH_DB_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchDB"
MAVI_SEARCH_AI_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchAI"
MAVI_SEARCH_FRAGMENT_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchVideoFragment"
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
    st.success("Video uploaded locally")

    if st.button("📡 Send to MAVI"):
        st.info("Sending video to MAVI...")

        with open(temp_filename, "rb") as video_file:
            files = {
                "file": (uploaded_file.name, video_file, "video/mp4")
            }
            headers = {
                "Authorization": MAVI_API_KEY
            }
            response = requests.post(MAVI_UPLOAD_URL, files=files, headers=headers)

        try:
            result = response.json()
            st.text(response.text)
        except Exception as e:
            st.error("❌ Failed to parse JSON response.")
            st.text(str(e))
            st.text(response.text)
            st.stop()

        if response.status_code == 200 and "data" in result and "videoNo" in result["data"]:
            video_no = result["data"]["videoNo"]
            st.session_state.video_no = video_no
            st.session_state.video_name = uploaded_file.name
            st.success(f"✅ Uploaded to MAVI! Video No: `{video_no}`")
        else:
            st.error("❌ Upload failed.")
            st.json(result)

st.subheader("🔍 Step 2: Search in Your Video")

# Create two columns for the search interface
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("Enter your search query", placeholder="What are you looking for?")
    
with col2:
    search_type = st.selectbox(
        "Search Type",
        ["keyword", "clip"],
        index=0,
        help="Choose between keyword search or clip search"
    )

if search_query and 'video_no' in st.session_state:
    if st.button("🔎 Search"):
        st.info("Searching in your video...")
        
        headers = {
            "Authorization": MAVI_API_KEY,
            "Content-Type": "application/json"
        }
        
        try:
            if search_type == "keyword":
                # Use searchAI endpoint for keyword search
                search_data = {
                    "searchValue": search_query
                }
                response = requests.post(
                    MAVI_SEARCH_AI_URL,
                    json=search_data,
                    headers=headers
                )
            else:  # clip search
                # Use searchVideoFragment endpoint for clip search
                search_data = {
                    "videoNos": [st.session_state.video_no],
                    "searchValue": search_query
                }
                response = requests.post(
                    MAVI_SEARCH_FRAGMENT_URL,
                    json=search_data,
                    headers=headers
                )
            
            st.write(f"Response status: {response.status_code}")
            
            try:
                result = response.json()
                st.write("Response body:", result)
                
                if response.status_code == 200:
                    if result.get("code") == "0000":  # Success code
                        if "data" in result:
                            st.success("✅ Search completed!")
                            
                            # Display search results
                            if search_type == "keyword":
                                # Handle video search results
                                for video in result["data"].get("videos", []):
                                    with st.expander(f"Video: {video.get('videoName', 'Unknown')}"):
                                        st.write(f"**Status:** {video.get('videoStatus', 'N/A')}")
                                        st.write(f"**Upload Time:** {video.get('uploadTime', 'N/A')}")
                            else:
                                # Handle clip search results
                                for video in result["data"].get("videos", []):
                                    with st.expander(f"Clip from {video.get('videoName', 'Unknown')}"):
                                        st.write(f"**Start Time:** {video.get('fragmentStartTime', 'N/A')}s")
                                        st.write(f"**End Time:** {video.get('fragmentEndTime', 'N/A')}s")
                                        st.write(f"**Duration:** {video.get('duration', 'N/A')}s")
                    else:
                        st.error(f"❌ API Error: {result.get('msg', 'Unknown error')}")
                        with st.expander("Error Details", expanded=True):
                            st.json(result)
                else:
                    st.error(f"❌ HTTP Error: {response.status_code}")
                    with st.expander("Error Details", expanded=True):
                        st.json(result)
                        
            except ValueError:
                st.error("❌ Invalid JSON response")
                st.write("Response text:", response.text)
                
        except Exception as e:
            st.error("❌ Error during search")
            with st.expander("Error Details", expanded=True):
                st.write(f"**Error Type:** {type(e).__name__}")
                st.write(f"**Error Message:** {str(e)}")
                if 'response' in locals():
                    st.write("**Response Status Code:**", response.status_code)
                    st.write("**Response Text:**")
                    st.text(response.text)
                st.write("**Request Details:**")
                st.json({
                    "url": MAVI_SEARCH_AI_URL if search_type == "keyword" else MAVI_SEARCH_FRAGMENT_URL,
                    "headers": {k: "***" if k == "Authorization" else v for k, v in headers.items()},
                    "data": search_data
                })
else:
    if not search_query:
        st.warning("Please enter a search query")
    elif 'video_no' not in st.session_state:
        st.warning("Please upload a video first")
