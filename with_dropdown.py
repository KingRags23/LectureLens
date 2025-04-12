import streamlit as st
import requests
import os
import time

# 🔐 API Keys
MAVI_API_KEY = "sk-7cd38706a5e62c9da49f8014ad69d346"
GEMINI_API_KEY = "AIzaSyAbGbaVPBR_2L3NzxAPWmIf2iwquZvv7yA"

# 🔗 Endpoints
MAVI_UPLOAD_URL = "https://mavi-backend.openinterx.com/api/serve/video/upload"
MAVI_SEARCH_DB_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchDB"
MAVI_SEARCH_AI_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchAI"
MAVI_SEARCH_FRAGMENT_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchVideoFragment"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
MAVI_SUB_TRANSCRIPTION_URL = "https://mavi-backend.openinterx.com/api/serve/video/subTranscription"
MAVI_GET_TRANSCRIPTION_URL = "https://mavi-backend.openinterx.com/api/serve/video/getTranscription"

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

    if st.button("📡 Send to MAVI", key="upload_button"):
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

if search_query:
    if st.button("🔎 Search", key="search_button"):
        st.info("Searching...")
        
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
                # First, get all videos from searchDB
                db_response = requests.get(
                    MAVI_SEARCH_DB_URL,
                    headers=headers
                )
                
                if db_response.status_code == 200:
                    db_result = db_response.json()
                    if db_result.get("code") == "0000":
                        # Extract video numbers from parsed videos
                        video_nos = [
                            video["videoNo"] 
                            for video in db_result["data"]["videoData"]
                            if video["videoStatus"] == "PARSE"
                        ]
                        
                        if not video_nos:
                            st.warning("No parsed videos found in the repository")
                            st.stop()
                            
                        # Use searchVideoFragment endpoint for clip search
                        search_data = {
                            "videoNos": video_nos,
                            "searchValue": search_query
                        }
                        response = requests.post(
                            MAVI_SEARCH_FRAGMENT_URL,
                            json=search_data,
                            headers=headers
                        )
                    else:
                        st.error(f"❌ Error getting videos: {db_result.get('msg', 'Unknown error')}")
                        st.stop()
                else:
                    st.error(f"❌ HTTP Error while getting videos: {db_response.status_code}")
                    st.stop()
            
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
                                        st.write(f"**Video ID:** `{video.get('videoNo', 'N/A')}`")
                                        st.write(f"**Status:** {video.get('videoStatus', 'N/A')}")
                                        st.write(f"**Upload Time:** {video.get('uploadTime', 'N/A')}")
                            else:
                                # Handle clip search results
                                for video in result["data"].get("videos", []):
                                    with st.expander(f"Clip from {video.get('videoName', 'Unknown')}"):
                                        # Video identification
                                        st.write(f"**Video ID:** `{video.get('videoNo', 'N/A')}`")
                                        
                                        # Convert string values to float for calculations
                                        try:
                                            start_time = float(video.get('fragmentStartTime', 0))
                                            end_time = float(video.get('fragmentEndTime', 0))
                                            total_duration = float(video.get('duration', 0))
                                            
                                            # Timing information
                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.write(f"**Start Time:** {start_time}s")
                                            with col2:
                                                st.write(f"**End Time:** {end_time}s")
                                            with col3:
                                                st.write(f"**Total Duration:** {total_duration}s")
                                            
                                            # Calculate and display clip duration
                                            clip_duration = end_time - start_time
                                            st.write(f"**Clip Duration:** {clip_duration}s")
                                            
                                            # Additional metadata
                                            upload_timestamp = int(video.get('uploadTime', 0))
                                            upload_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(upload_timestamp/1000))
                                            st.write(f"**Upload Time:** {upload_time}")
                                            st.write(f"**Status:** {video.get('videoStatus', 'N/A')}")
                                            
                                            # Add a visual timeline representation
                                            progress_text = "Video Timeline"
                                            timeline_width = end_time/total_duration * 100
                                            timeline_start = start_time/total_duration * 100
                                            st.write(progress_text)
                                            st.progress(timeline_width/100)
                                            
                                        except (ValueError, TypeError) as e:
                                            st.error(f"Error processing video data: {str(e)}")
                                            st.json(video)  # Display raw video data for debugging
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

st.subheader("📝 Step 3: Get Video Transcription")

def fetch_video_numbers():
    """Fetch parsed video numbers from MAVI API"""
    headers = {"Authorization": MAVI_API_KEY}
    try:
        response = requests.get(MAVI_SEARCH_DB_URL, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "0000" and "videoData" in data.get("data", {}):
                videos = data["data"]["videoData"]
                # Return video numbers with names for better display
                return [(f"{video['videoNo']} - {video.get('videoName', 'Unnamed')}", video['videoNo']) 
                        for video in videos if video["videoStatus"] == "PARSE"]
            else:
                st.error(f"Error fetching videos: {data.get('msg', 'Unknown error')}")
                return []
        else:
            st.error(f"HTTP Error: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Failed to fetch videos: {str(e)}")
        return []

# Fetch video numbers for dropdown
video_options = fetch_video_numbers()

if video_options:
    # Format: Display text, actual value
    display_options = [option[0] for option in video_options]
    video_values = [option[1] for option in video_options]
    
    selected_index = st.selectbox(
        "Select Video",
        options=range(len(display_options)),
        format_func=lambda i: display_options[i],
        help="Choose from uploaded videos"
    )
    
    # Get the actual video number from the selected index
    video_no = video_values[selected_index]
    
    # Show the selected video number (helpful for debugging)
    st.caption(f"Selected Video No: {video_no}")
else:
    st.warning("No parsed videos available. Please upload and process videos first.")
    # Provide a fallback text input in case the API call fails
    video_no = st.text_input("Enter Video No manually", value="")

transcription_type = st.selectbox(
    "Transcription Type",
    ["AUDIO", "VIDEO", "AUDIO/VIDEO"],
    index=0,
    help="Choose the type of transcription"
)

# Fixed button with a single instance and conditional check inside
if st.button("Get Transcription", key="transcription_button"):
    if not video_no:
        st.error("Please select a video first.")
    else:
        st.info(f"Requesting transcription for video: {video_no}...")
        
        headers = {
            "Authorization": MAVI_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Step 1: Submit transcription task
        sub_data = {
            "videoNo": video_no,
            "type": transcription_type
        }
        
        try:
            # Submit transcription task
            with st.spinner("Submitting transcription request..."):
                sub_response = requests.post(
                    MAVI_SUB_TRANSCRIPTION_URL,
                    json=sub_data,
                    headers=headers
                )
            
            if sub_response.status_code == 200:
                sub_result = sub_response.json()
                if sub_result.get("code") == "0000":  # Success code
                    task_no = sub_result["data"]["taskNo"]
                    st.success(f"✅ Transcription task submitted! Task No: {task_no}")
                    
                    # Create placeholders for displaying results
                    status_placeholder = st.empty()
                    type_placeholder = st.empty()
                    content_placeholder = st.empty()
                    
                    # Try up to 30 times (5 minutes)
                    with st.spinner("Processing transcription..."):
                        for attempt in range(1, 31):
                            status_placeholder.info(f"Checking transcription status (attempt {attempt}/30)...")
                            
                            # Step 2: Get transcription results
                            params = {"taskNo": task_no}
                            get_response = requests.get(
                                MAVI_GET_TRANSCRIPTION_URL,
                                headers=headers,
                                params=params
                            )
                            
                            if get_response.status_code == 200:
                                get_result = get_response.json()
                                if get_result.get("code") == "0000":
                                    transcription_data = get_result.get("data", {})
                                    
                                    # Display transcription status
                                    status = transcription_data.get('status', 'N/A')
                                    status_placeholder.write(f"**Status:** {status}")
                                    type_placeholder.write(f"**Type:** {transcription_data.get('type', 'N/A')}")
                                    
                                    # Display transcription content
                                    transcriptions = transcription_data.get("transcriptions", [])
                                    
                                    if transcriptions:
                                        content = content_placeholder.container()
                                        content.subheader("Transcription Content:")
                                        
                                        # Format timestamp function
                                        def format_timestamp(seconds):
                                            try:
                                                seconds_float = float(seconds)
                                                hours = int(seconds_float // 3600)
                                                minutes = int((seconds_float % 3600) // 60)
                                                seconds = int(seconds_float % 60)
                                                if hours > 0:
                                                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                                return f"{minutes:02d}:{seconds:02d}"
                                            except (ValueError, TypeError):
                                                return "00:00"
                                        
                                        # Create formatted transcript with timestamps
                                        for idx, trans in enumerate(transcriptions):
                                            start_time = format_timestamp(trans.get('startTime', 0))
                                            end_time = format_timestamp(trans.get('endTime', 0))
                                            
                                            with content.expander(f"Segment {idx + 1}"):
                                                content.markdown(f"**Time:** [{start_time} - {end_time}]")
                                                content.markdown("---")
                                                content.write(trans.get("content", "No content available"))
                                        
                                        # Add download button for the full transcript
                                        full_transcript = "\n\n".join([
                                            f"[{format_timestamp(t.get('startTime', 0))} - {format_timestamp(t.get('endTime', 0))}]\n{t.get('content', '')}"
                                            for t in transcriptions
                                        ])
                                        
                                        content.download_button(
                                            "📥 Download Full Transcript",
                                            full_transcript,
                                            "transcript.txt",
                                            "Download the complete transcript with timestamps"
                                        )
                                        
                                        # Exit loop if finished
                                        if status == 'FINISH':
                                            status_placeholder.success("✅ Transcription completed!")
                                            break
                                    else:
                                        content_placeholder.warning("No transcription content available yet. The process might still be ongoing.")
                                    
                                    # Wait and retry if unfinished
                                    if status == 'UNFINISHED':
                                        time.sleep(10)
                                        continue
                                    # Exit loop if failed
                                    elif status == 'FAIL':
                                        status_placeholder.error("❌ Transcription process failed.")
                                        break
                                else:
                                    st.error(f"❌ Error getting transcription: {get_result.get('msg', 'Unknown error')}")
                                    break
                            else:
                                st.error(f"❌ HTTP Error while getting transcription: {get_response.status_code}")
                                break
                        else:
                            st.warning("Transcription process timed out. Please try again later.")
                else:
                    st.error(f"❌ Error submitting transcription task: {sub_result.get('msg', 'Unknown error')}")
            else:
                st.error(f"❌ HTTP Error while submitting task: {sub_response.status_code}")
                st.code(sub_response.text)
                
        except Exception as e:
            st.error("❌ Error during transcription process")
            with st.expander("Error Details", expanded=True):
                st.write(f"**Error Type:** {type(e).__name__}")
                st.write(f"**Error Message:** {str(e)}")
