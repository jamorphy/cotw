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
        save_clips_metadata(work_dir, en_clips)
        download_clips(work_dir)
        return f"Successfully retrieved {len(en_clips)} clips."
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def save_clips_metadata(work_dir, clips, min_views=800):
    filtered_clips = [clip for clip in clips if clip['view_count'] > min_views]
    for clip in filtered_clips:
        if isinstance(clip['created_at'], datetime):
            clip['created_at'] = clip['created_at'].isoformat()
        clip['is_analyzed'] = False

        if "embed_url" in clip:
            del clip["embed_url"]
        if "broadcaster_id" in clip:
            del clip["broadcaster_id"]
        if "creator_id" in clip:
            del clip["creator_id"]
        if "creator_name" in clip:
            del clip["creator_name"]
        if "video_id" in clip:
            del clip["video_id"]
        if "vod_offset" in clip:
            del clip["vod_offset"]
        if "is_featured" in clip:
            del clip["is_featured"]

    metadata_path = os.path.join(work_dir, 'clips_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(filtered_clips, f, indent=2)



    print(f"Metadata saved to {metadata_path}")

def download_clips(work_dir):
    with open(os.path.join(work_dir, 'clips_metadata.json'), 'r') as f:
        clips_metadata = json.load(f)

    def download_clip(clip):
        clip_id = clip['id']
        clip_url = clip['url']
        clip_dir = os.path.join(work_dir, 'clips', clip_id)
        os.makedirs(clip_dir, exist_ok=True)
        video_output_template = os.path.join(clip_dir, f"{clip_id}_video.%(ext)s")
        audio_output_template = os.path.join(clip_dir, f"{clip_id}_audio")

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
                video_info = ydl.extract_info(clip_url, download=True)

            with yt_dlp.YoutubeDL(audio_ydl_opts) as ydl:
                audio_info = ydl.extract_info(clip_url, download=True)

            clip['video_path'] = os.path.join(clip_dir, f"{clip_id}_video.mp4")
            clip['audio_path'] = os.path.join(clip_dir, f"{clip_id}_audio.mp3")
            return clip
        except Exception as e:
            print(f"Error downloading clip {clip['id']}: {str(e)}")
            return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_clip, clip) for clip in clips_metadata]

        updated_clips = []
        with tqdm(total=len(futures), desc="Downloading clips") as pbar:
            for future in as_completed(futures):
                updated_clip = future.result()
                if updated_clip:
                    updated_clips.append(updated_clip)
                    pbar.set_postfix(video=updated_clip['video_path'], audio=updated_clip['audio_path'])
                pbar.update(1)

    with open(os.path.join(work_dir, 'clips_metadata.json'), 'w') as f:
        json.dump(updated_clips, f, indent=2)