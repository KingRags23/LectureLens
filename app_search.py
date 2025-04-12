import streamlit as st
import requests
import os
import time
import cv2
import numpy as np
import yaml

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

# 関数定義を使用箇所の前に移動
def get_clip_transcription(video_no, start_time, end_time, transcriptions):
    clip_transcriptions = []
    for trans in transcriptions:
        trans_start = float(trans.get('startTime', 0))
        trans_end = float(trans.get('endTime', 0))
        
        # クリップの時間範囲と重なるトランスクリプションを抽出
        if (trans_start <= end_time and trans_end >= start_time):
            clip_transcriptions.append(trans)
    
    return clip_transcriptions

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

# ビデオを取得する関数を修正
def get_video_content(video_no):
    """Get video content either from local file or API"""
    # First try to get from local file
    try:
        with open('video_mapping.yaml', 'r') as f:
            video_map = yaml.safe_load(f)
            if video_no in video_map['videos']:
                file_path = video_map['videos'][video_no]
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        return f.read()
    except Exception as e:
        st.warning(f"Local file not found: {str(e)}")
    
    # If local file not found, try API
    url = f"https://mavi-backend.openinterx.com/api/serve/video/get/{video_no}"
    headers = {
        "Authorization": MAVI_API_KEY
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Failed to get video: Status code {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error getting video: {str(e)}")
        return None

def process_video_clip(video_content, start_time, end_time, video_no):
    """Process video to display original video with specified start time"""
    try:
        # Save the video content to a temporary file
        temp_input = f"temp_input_{video_no}.mp4"
        with open(temp_input, "wb") as f:
            f.write(video_content)
        
        # Return the original video path and start time
        return temp_input, start_time
    except Exception as e:
        st.error(f"Error processing video: {str(e)}")
        return None, None

st.subheader("🔍 Step 2: Search in Your Video")

# Create two columns for the search interface
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("Enter your search query", placeholder="What are you looking for?")
    
with col2:
    search_type = st.selectbox(
        "Search Type",
        ["keyword", "clip"],
        index=1,
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
                                        upload_timestamp = int(video.get('uploadTime', 0))
                                        upload_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(upload_timestamp/1000))
                                        st.write(f"**Upload Time:** {upload_time}")
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
                                                
                                                # 空のプログレスバーを表示（全体の長さを表現）
                                                empty_progress = st.empty()
                                                empty_progress.progress(0.0)
                                                
                                                # クリップの区間を表示するプログレスバー
                                                # カスタムスタイルでプログレスバーの位置と長さを設定
                                                progress_html = f"""
                                                <div style="position: relative; margin-top: -40px;">
                                                    <div style="
                                                        position: absolute;
                                                        left: {timeline_start}%;
                                                        width: {timeline_width}%;
                                                        height: 6px;
                                                        background-color: #0078D4;
                                                        border-radius: 3px;
                                                    "></div>
                                                </div>
                                                """
                                                st.markdown(progress_html, unsafe_allow_html=True)
                                                
                                            except (ValueError, TypeError) as e:
                                                st.error(f"Error processing video data: {str(e)}")
                                                st.json(video)  # Display raw video data for debugging

                                            # トランスクリプションを取得
                                            headers = {
                                                "Authorization": MAVI_API_KEY,
                                                "Content-Type": "application/json"
                                            }
                                            
                                            # トランスクリプションタスクを送信
                                            sub_data = {
                                                "videoNo": video.get('videoNo'),
                                                "type": "AUDIO"  # または "AUDIO/VIDEO" for both
                                            }
                                            
                                            sub_response = requests.post(
                                                MAVI_SUB_TRANSCRIPTION_URL,
                                                json=sub_data,
                                                headers=headers
                                            )
                                            
                                            if sub_response.status_code == 200:
                                                sub_result = sub_response.json()
                                                if sub_result.get("code") == "0000":
                                                    task_no = sub_result["data"]["taskNo"]
                                                    
                                                    # トランスクリプション結果を取得
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
                                                            
                                                            if transcription_data.get('status') == 'FINISH':
                                                                start_time = float(video.get('fragmentStartTime', 0))
                                                                end_time = float(video.get('fragmentEndTime', 0))
                                                                
                                                                # クリップの時間範囲のトランスクリプションを取得
                                                                clip_transcriptions = get_clip_transcription(
                                                                    video.get('videoNo'),
                                                                    start_time,
                                                                    end_time,
                                                                    transcription_data.get('transcriptions', [])
                                                                )
                                                                
                                                                # トランスクリプションを表示
                                                                if clip_transcriptions:
                                                                    st.subheader("Clip Transcription")
                                                                    for trans in clip_transcriptions:
                                                                        trans_start = float(trans.get('startTime', 0))
                                                                        trans_end = float(trans.get('endTime', 0))
                                                                        st.markdown(f"**[{trans_start:.2f}s - {trans_end:.2f}s]**")
                                                                        st.write(trans.get('content', ''))
                                                                else:
                                                                    st.info("No transcription available for this clip")
                                                            else:
                                                                st.warning("Transcription process not finished")
                                                        else:
                                                            st.error(f"❌ Error getting transcription: {get_result.get('msg', 'Unknown error')}")
                                                    else:
                                                        st.error(f"❌ HTTP Error while getting transcription: {get_response.status_code}")
                                            else:
                                                st.error(f"❌ HTTP Error while submitting task: {sub_response.status_code}")

                                            # ビデオを表示
                                            try:
                                                video_content = get_video_content(video.get('videoNo'))
                                                if video_content:
                                                    # クリップ処理を実行
                                                    start_time = float(video.get('fragmentStartTime', 0))
                                                    end_time = float(video.get('fragmentEndTime', 0))
                                                    video_path, start_time = process_video_clip(video_content, start_time, end_time, video.get('videoNo'))
                                                    
                                                    if video_path and os.path.exists(video_path):
                                                        # オリジナルのビデオを表示し、開始位置を指定
                                                        st.video(video_path, start_time=int(start_time))
                                                        # 使用後は一時ファイルを削除
                                                        try:
                                                            os.remove(video_path)
                                                        except:
                                                            pass  # Ignore cleanup errors
                                                    else:
                                                        st.error("Failed to find video file")
                                            except Exception as e:
                                                st.error(f"Failed to display video: {str(e)}")
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
video_options = fetch_video_numbers()
if video_options:
    selected_option = st.selectbox(
        "Select Video",
        options=[option[0] for option in video_options],
        index=0
    )
    # Get the actual video number from the selected option
    video_no = [option[1] for option in video_options if option[0] == selected_option][0]
else:
    video_no = st.text_input("Enter Video No", value="mavi_video_566050240969445376")
    st.warning("No parsed videos available. Please enter video number manually.")

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
