from youtube_transcript_api import YouTubeTranscriptApi

video_id = "spUNpyF58BY" # 3Blue1Brown video
api = YouTubeTranscriptApi()

try:
    print("Fetching list...")
    t_list = api.list(video_id)
    print("Available transcripts (auto-generated?):")
    for t in t_list:
        print(f" - {t.language_code} (Generated: {t.is_generated})")
    
    print("\nTrying to find best English transcript...")
    try:
        t = t_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        print("Found Manually created:", t.language_code)
    except Exception as e1:
        print("Manual failed:", e1)
        try:
            t = t_list.find_generated_transcript(["en", "en-US", "en-GB"])
            print("Found Generated:", t.language_code)
        except Exception as e2:
            print("Generated failed:", e2)
            t = list(t_list)[0].translate('en')
            print("Fell back to translating first available -> English")
    
    data = t.fetch()
    print("SUCCESS, grabbed chunks:", len(data))
except Exception as e:
    print("Fatal exception:", e)
