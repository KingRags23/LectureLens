import requests
import warnings

# === SUPPRESS SSL WARNINGS ===
warnings.filterwarnings("ignore", category=UserWarning)

# === CONFIGURATION ===
MAVI_API_KEY = "sk-7cd38706a5e62c9da49f8014ad69d346"
MAVI_SEARCH_DB_URL = "https://mavi-backend.openinterx.com/api/serve/video/searchDB"
MAVI_DELETE_VIDEO_URL = "https://mavi-backend.openinterx.com/api/serve/video/delete"

HEADERS = {
    "Authorization": MAVI_API_KEY,
    "Content-Type": "application/json"
}

# === STEP 1: FETCH VIDEO LIST ===
def fetch_video_ids():
    video_ids = []
    page = 1
    page_size = 50

    while True:
        params = {
            "page": page,
            "pageSize": page_size
        }

        print(f"\n📡 Sending GET request to: {MAVI_SEARCH_DB_URL}")
        response = requests.get(MAVI_SEARCH_DB_URL, params=params, headers=HEADERS)

        print(f"✅ Response Code: {response.status_code}")
        print("🔎 Raw response text:", response.text)

        if response.status_code != 200:
            print(f"❌ Failed to fetch videos on page {page}: {response.text}")
            break

        result = response.json()

        # ✅ Correct key for video list
        videos = result.get("data", {}).get("videoData", [])

        if not videos:
            print("ℹ️ No video entries found in 'videoData'.")
            break

        for video in videos:
            video_no = video.get("videoNo")
            video_name = video.get("videoName", "Unknown")
            print(f"📄 Found video: {video_name} (videoNo: {video_no})")
            if video_no:
                video_ids.append(video_no)

        page += 1

    return video_ids

# === STEP 2: DELETE ALL VIDEOS IN BULK ===
def delete_videos(video_ids):
    if not video_ids:
        print("🚫 No videos to delete.")
        return

    print(f"\n🚀 Sending DELETE request for {len(video_ids)} videos...")

    response = requests.delete(
        MAVI_DELETE_VIDEO_URL,
        headers=HEADERS,
        json=video_ids  # MUST be a plain array per MAVI docs
    )

    print(f"✅ DELETE Status Code: {response.status_code}")
    try:
        print("📝 Response JSON:", response.json())
    except Exception as e:
        print("❌ Failed to parse response:", str(e))
        print(response.text)

# === MAIN SCRIPT ===
if __name__ == "__main__":
    print("📥 Fetching all videos linked to your MAVI account...")
    video_ids = fetch_video_ids()

    if video_ids:
        delete_videos(video_ids)
    else:
        print("✅ No videos found to delete.")
