# editor.py
#
#
# Checks if a video can be created, then creates it
import autogen
import os
os.environ["IMAGEIO_FFMPEG_EXE"] = "/opt/homebrew/bin/ffmpeg"
import yaml
import json
import argparse
from util import get_working_folder, get_editor_info
from autogen import ConversableAgent
from agents import editor

from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.fx.all import resize
from moviepy.config import change_settings
from tqdm import tqdm

# Checks clips_metadata.json if there are enough clips to create a video
def check_total_runtime(work_dir, target_runtime):
    metadata_path = os.path.join(work_dir, "clips_metadata.json")
    with open(metadata_path, 'r') as f:
        clips_metadata = json.load(f)

    runtime = 0
    for clips in clips_metadata:
        runtime += clips['duration']

    return runtime


def compile_video(work_dir):
    metadata_path = os.path.join(work_dir, "clips_metadata.json")
    with open(metadata_path, 'r') as f:
        clips_metadata = json.load(f)

    final_clips = []
    target_resolution = (1920, 1080)

    for clip in tqdm(clips_metadata, desc="Processing clips"):
        if 'video_path' not in clip:
            continue
        
        clip_path = clip['video_path']
        video = VideoFileClip(clip_path)
        video = video.resize(height=target_resolution[1])
        video = video.crop(x_center=video.w/2, y_center=video.h/2, 
                           width=target_resolution[0], height=target_resolution[1])
        final_clips.append(video)

    print("Concatenating clips...")
    compiled_video = concatenate_videoclips(final_clips)
    output_dir = os.path.join(work_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'compilation.mp4')

    print(f"Rendering final video to {output_path}...")
    compiled_video.write_videofile(output_path, codec='libx264', audio_codec='aac')

    # Cleanup
    compiled_video.close()
    for clip in final_clips:
        clip.close()
    
    print(f"Compilation complete!")
    return output_path


available_functions = {
    "check_total_runtime": check_total_runtime,
    "compile_video": compile_video
}

single_turn_config = {
    "config_list": [{"model": "gpt-4o-mini", "api_key": os.environ["OPENAI_API_KEY"], "api_type": "openai"}]
}

single_turn = ConversableAgent(
    "singleturn",
    system_message="You make agents terminate when they complete their task.",
    llm_config=single_turn_config,
    human_input_mode="NEVER",
    function_map=available_functions
)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("game_name", help="Name of game to analyze")
    args = parser.parse_args()

    with open("metadata.yaml", "r") as f:
        games = yaml.safe_load(f)["games"] 

    min_views, min_runtime = get_editor_info(games, args.game_name)

    working_folder = get_working_folder(args.game_name)
    if working_folder:
        print(f'Active folder exists: {working_folder}, starting analysis.')
    else:
        print(f'No active folder exists for \'{args.game_name}\', terminating analysis.')
        exit(1)    
    
    single_turn.initiate_chat(
        editor,
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
        message=f"Let's check if there's enough runtime to compile a video, work_dir: {working_folder}, target_runtime: {min_runtime}",
    )
