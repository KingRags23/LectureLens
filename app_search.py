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

if search_query:
    if st.button("🔎 Search"):
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
                # st.write("Response body:", result)  # この行をコメントアウトまたは削除
                
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
                                videos = result["data"].get("videos", [])
                                
                                # クリップをマージする関数
                                def should_merge_clips(clip1, clip2, threshold=5):
                                    start1 = float(clip1.get('fragmentStartTime', 0))
                                    end1 = float(clip1.get('fragmentEndTime', 0))
                                    start2 = float(clip2.get('fragmentStartTime', 0))
                                    end2 = float(clip2.get('fragmentEndTime', 0))
                                    
                                    # 重複または近接（threshold秒以内）している場合はマージ
                                    return start2 <= end1 + threshold

                                def merge_clips(clips):
                                    if not clips:
                                        return []
                                        
                                    # 開始時間でソート
                                    sorted_clips = sorted(clips, key=lambda x: float(x.get('fragmentStartTime', 0)))
                                    merged = []
                                    current_group = [sorted_clips[0]]
                                    
                                    for clip in sorted_clips[1:]:
                                        if should_merge_clips(current_group[-1], clip):
                                            current_group.append(clip)
                                        else:
                                            # 新しいグループを作成
                                            if current_group:
                                                # グループ内の最小開始時間と最大終了時間を取得
                                                start = min(float(c.get('fragmentStartTime', 0)) for c in current_group)
                                                end = max(float(c.get('fragmentEndTime', 0)) for c in current_group)
                                                
                                                # マージされたクリップを作成
                                                merged_clip = dict(current_group[0])
                                                merged_clip['fragmentStartTime'] = start
                                                merged_clip['fragmentEndTime'] = end
                                                merged.append(merged_clip)
                                            
                                            current_group = [clip]
                                    
                                    # 最後のグループを処理
                                    if current_group:
                                        start = min(float(c.get('fragmentStartTime', 0)) for c in current_group)
                                        end = max(float(c.get('fragmentEndTime', 0)) for c in current_group)
                                        merged_clip = dict(current_group[0])
                                        merged_clip['fragmentStartTime'] = start
                                        merged_clip['fragmentEndTime'] = end
                                        merged.append(merged_clip)
                                    
                                    return merged
                                
                                # 同じvideoNoのクリップをグループ化
                                video_groups = {}
                                for video in videos:
                                    video_no = video.get('videoNo')
                                    if video_no not in video_groups:
                                        video_groups[video_no] = []
                                    video_groups[video_no].append(video)
                                
                                # 各グループ内でクリップをマージ
                                for video_no, group in video_groups.items():
                                    merged_clips = merge_clips(group)
                                    
                                    # マージされたクリップを表示
                                    for video in merged_clips:
                                        with st.expander(f"Clip from {video.get('videoName', 'Unknown')}"):
                                            # 以下は既存のコード
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
                                                timeline_width = (end_time - start_time) / total_duration * 100
                                                timeline_start = start_time / total_duration * 100
                                                st.write(progress_text)
                                                
                                                # タイムラインの位置を視覚的に表示
                                                st.markdown(f"<div style='margin-bottom: 5px;'>Full video: {total_duration}s</div>", unsafe_allow_html=True)
                                                st.progress(timeline_start/100)  # クリップの開始位置
                                                st.progress(timeline_width/100)  # クリップの長さ
                                                
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

# トランスクリプションを取得するための入力フィールドとボタン
video_no = st.text_input("Enter Video No", value="mavi_video_566050240969445376")
transcription_type = st.selectbox(
    "Transcription Type",
    ["AUDIO", "VIDEO", "AUDIO/VIDEO"],
    index=0,
    help="Choose the type of transcription"
)

if st.button("Get Transcription"):
    st.info("Requesting transcription...")
    
    headers = {
        "Authorization": MAVI_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Step 1: トランスクリプションタスクを送信
    sub_data = {
        "videoNo": video_no,
        "type": transcription_type
    }
    
    try:
        # トランスクリプションタスクを送信
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
                
                # 結果表示用のプレースホルダーを作成
                status_placeholder = st.empty()
                type_placeholder = st.empty()
                content_placeholder = st.empty()
                
                # 最大30回（5分間）試行
                for _ in range(30):
                    # Step 2: トランスクリプション結果を取得
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
                            
                            # トランスクリプションの状態を表示
                            status_placeholder.write(f"**Status:** {transcription_data.get('status', 'N/A')}")
                            type_placeholder.write(f"**Type:** {transcription_data.get('type', 'N/A')}")
                            
                            # トランスクリプションの内容を表示
                            transcriptions = transcription_data.get("transcriptions", [])
                            
                            if transcriptions:
                                content = content_placeholder.container()
                                content.subheader("Transcription Content:")
                                
                                def format_timestamp(seconds):
                                    try:
                                        # Convert seconds to float first
                                        seconds_float = float(seconds)
                                        hours = int(seconds_float // 3600)
                                        minutes = int((seconds_float % 3600) // 60)
                                        seconds = int(seconds_float % 60)
                                        if hours > 0:
                                            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                        return f"{minutes:02d}:{seconds:02d}"
                                    except (ValueError, TypeError):
                                        return "00:00"  # Return default value if conversion fails
                                
                                # Create a formatted transcript with timestamps
                                for idx, trans in enumerate(transcriptions):
                                    start_time = format_timestamp(trans.get('startTime', 0))
                                    end_time = format_timestamp(trans.get('endTime', 0))
                                    
                                    with content.expander(f"Segment {idx + 1}"):
                                        # Display timestamp and content
                                        content.markdown(f"**Time:** [{start_time} - {end_time}]")
                                        content.markdown("---")  # Separator
                                        content.write(trans.get("content", "No content available"))
                                
                                # Add a download button for the full transcript
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
                                
                                # 完了したら終了
                                if transcription_data.get('status') == 'FINISH':
                                    break
                            else:
                                content_placeholder.warning("No transcription content available yet. The process might still be ongoing.")
                            
                            # UNFINISHEDの場合は10秒待って再試行
                            if transcription_data.get('status') == 'UNFINISHED':
                                time.sleep(10)
                                continue
                            
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
            
    except Exception as e:
        st.error("❌ Error during transcription process")
        with st.expander("Error Details", expanded=True):
            st.write(f"**Error Type:** {type(e).__name__}")
            st.write(f"**Error Message:** {str(e)}")
