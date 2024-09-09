import requests
from datetime import datetime, timedelta
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import yt_dlp

CLIENT_ID = "zc6zd5ktlm94jg0hq7a59fg8cvfsb8"
CLIENT_SECRET = "k7ugx8ab7hhgx8h864c0w1hokpmkpv"

def get_oauth_token():
    auth_url = "https://id.twitch.tv/oauth2/token"
    auth_params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    auth_response = requests.post(auth_url, params=auth_params)
    return auth_response.json()["access_token"]

def get_top_clips(game_id, work_dir, limit=30):
    access_token = get_oauth_token()
    
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    
    one_day_ago = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
    
    clips_url = "https://api.twitch.tv/helix/clips"
    params = {
        "game_id": game_id,
        "first": 65,
        "started_at": one_day_ago,
        "language": "en"
    }
    
    response = requests.get(clips_url, headers=headers, params=params)
    
    if response.status_code == 200:
        clips = response.json()["data"]
        en_clips = [clip for clip in clips if clip['language'] == 'en']
        save_clips_metadata(en_clips)
        download_clips(work_dir )
        return "Finished retrieving top clips."
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def save_clips_metadata(clips, filename='clips_metadata.json', min_views=500):
    filtered_clips = [clip for clip in clips if clip['view_count'] > min_views]
    for clip in filtered_clips:
        if isinstance(clip['created_at'], datetime):
            clip['created_at'] = clip['created_at'].isoformat()

    with open(filename, 'w') as f:
        json.dump(filtered_clips, f, indent=2)
    print(f"Metadata saved to {filename}")

def download_clips(work_dir):
    with open('clips_metadata.json', 'r') as f:
        clips_metadata = json.load(f)

    def download_clip(clip):
        clip_id = clip['id']
        clip_url = clip['url']
        clip_dir = os.path.join(work_dir, 'clips', clip_id)
        os.makedirs(clip_dir, exist_ok=True)
        video_output_template = os.path.join(clip_dir, f"{clip_id}.%(ext)s")
        audio_output_template = os.path.join(clip_dir, f"{clip_id}.mp3")

        video_ydl_opts = {
            'outtmpl': video_output_template,
            'quiet': True,
            'no_warnings': True,
        }

        audio_ydl_opts = {
            'outtmpl': audio_output_template,
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(video_ydl_opts) as ydl:
                ydl.download([clip_url])

            with yt_dlp.YoutubeDL(audio_ydl_opts) as ydl:
                ydl.download([clip_url])

            return video_output_template, audio_output_template
        except Exception as e:
            print(f"Error downloading clip {clip['id']}: {str(e)}")
            return None, None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_clip, clip) for clip in clips_metadata]

        with tqdm(total=len(futures), desc="Downloading clips") as pbar:
            for future in as_completed(futures):
                video_path, audio_path = future.result()
                if video_path and audio_path:
                    pbar.set_postfix(video=video_path, audio=audio_path)
                pbar.update(1)