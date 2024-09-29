import requests
from datetime import datetime, timedelta
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import yt_dlp
import yaml

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

def get_top_clips(game_id, work_dir, min_views, limit=20):
    access_token = get_oauth_token()
    
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    
    one_day_ago = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
    
    clips_url = "https://api.twitch.tv/helix/clips"
    params = {
        "game_id": game_id,
        "first": limit,
        "started_at": one_day_ago,
        "language": "en",
    }
    
    response = requests.get(clips_url, headers=headers, params=params)
    
    if response.status_code == 200:
        clips = response.json()["data"]
        # TODO: We are gathering clips from all languages for testing purposes
        # en_clips = [clip for clip in clips if clip['language'] == 'en']
        save_clips_metadata(work_dir, clips, min_views)
        download_all_clips(work_dir)
        return f"Retrieved {len(clips)} clips from the Twitch API."
    else:
        print(f"Error {response.status_code} fetching from Twitch API: {response.text}")
        return None

def save_clips_metadata(work_dir, clips, min_views=1000):
    metadata_path = os.path.join(work_dir, 'clips_metadata.json')
    
    existing_clips = []
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            existing_clips = json.load(f)

    print(f"There are {len(existing_clips)} existing clips.")
    
    filtered_clips = [clip for clip in clips if clip['view_count'] > int(min_views)]

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

    all_clips = existing_clips + filtered_clips

    print(f"About to save, there are {len(all_clips)} total clips.")

    with open(metadata_path, 'w') as f:
        json.dump(all_clips, f, indent=2)

    print(f"Metadata saved to {metadata_path}")

def download_clip(work_dir, clip):
    clip_id = clip['id']
    clip_url = clip['url']
    clip_dir = os.path.join(work_dir, 'clips', clip_id)
    os.makedirs(clip_dir, exist_ok=True)
    video_output_template = os.path.join(clip_dir, f"{clip_id}_video.%(ext)s")
    audio_output_template = os.path.join(clip_dir, f"{clip_id}_audio")

    with open('metadata.yaml', 'r') as f:
        metadata = yaml.safe_load(f)

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    ffmpeg_location = config['ffmpeg_path']

    video_ydl_opts = {
        'outtmpl': video_output_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': ffmpeg_location
    }

    audio_ydl_opts = {
        'outtmpl': audio_output_template,
        'quiet': True,
        'no_warnings': True,
        'format': 'bestaudio/best',
        'ffmpeg_location': ffmpeg_location,
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

def download_all_clips(work_dir):
    metadata_path = os.path.join(work_dir, 'clips_metadata.json')
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    analyzed_clips = [
        clip for clip in metadata if clip['is_analyzed']
    ]

    clips_to_download = [
        clip for clip in metadata
        if 'video_path' not in clip
        or 'audio_path' not in clip
    ]

    print(f'there are {len(clips_to_download)} clips to download')

    if len(clips_to_download) > 0:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(lambda clip=clip: download_clip(work_dir, clip), clip) for clip in clips_to_download]

            updated_clips = []
            with tqdm(total=len(futures), desc="Downloading clips") as pbar:
                for future in as_completed(futures):
                    updated_clip = future.result()
                    if updated_clip:
                        updated_clips.append(updated_clip)
                        pbar.set_postfix(video=updated_clip['video_path'], audio=updated_clip['audio_path'])
                    pbar.update(1)

    final_clips = analyzed_clips + updated_clips

    with open(metadata_path, 'w') as f:
        json.dump(final_clips, f, indent=2)