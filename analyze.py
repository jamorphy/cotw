# analyze.py
#
# Analyze the clips in the active game folder
#
#
import autogen
import re
import os
import argparse
import yaml
import json

from util import get_working_folder, get_game_info
from agents import content, metrics, orchestrator

from send_discord_message import send_message

def get_clip_scores(message):
    relevant_content = message['content'].split("TERMINATE")[0].strip()

    score_match = re.search(r'final_score:\s*(\d+)', relevant_content)
    score = int(score_match.group(1)) if score_match else None

    keywords_match = re.search(r'keywords:\s*(.+)', relevant_content)
    keywords = keywords_match.group(1).split(', ') if keywords_match else []

    reasoning_match = re.search(r'reasoning:\s*(.+)', relevant_content, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

    return {
        "score": score,
        "keywords": keywords,
        "reasoning": reasoning
    }

def analyze_clip(clip_data):
    initial_message = f"""
    Let's evaluate the following clip:
    
    Title: {clip_data['title']}
    Duration: {clip_data['duration']} seconds
    View Count: {clip_data['view_count']}
    Streamer name: {clip_data['broadcaster_name']}
    
    Transcription:
    {clip_data['transcription']}

    Visual Summary:
    {clip_data['summary']}
    
    Let's begin.
    """
    
    groupchat = autogen.GroupChat(
        agents=[content, metrics, orchestrator],
        messages=[],
        max_round=15,
        speaker_selection_method="round_robin"
    )

    def print_messages(recipient, messages, sender, config):
        if "callback" in config and  config["callback"] is not None:
            callback = config["callback"]
            callback(sender, recipient, messages[-1])
        return False, None
    
    manager = autogen.GroupChatManager(groupchat=groupchat)

    manager.initiate_chat(
        manager,
        message=initial_message
    )

    result = get_clip_scores(groupchat.messages[-1])
    return result

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("game_name", help="Name of game to analyze")
    args = parser.parse_args()

    with open("metadata.yaml", "r") as f:
        games = yaml.safe_load(f)["games"] 

    game_id, game_display, _, discord_channel_id = get_game_info(games, args.game_name)

    send_message(f'Analyzing clips for: {args.game_name}', discord_channel_id)

    working_folder = get_working_folder(args.game_name)
    if working_folder:
        print(f'Active folder exists: {working_folder}, starting analysis.')
    else:
        print(f'No active folder exists for \'{args.game_name}\', terminating analysis.')
        exit(1)


    metadata_file = os.path.join(working_folder, 'clips_metadata.json')
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)


    analyzed_clips = [
        clip for clip in metadata if clip['is_analyzed']
    ]
    clips_to_analyze = [
        clip for clip in metadata if not clip['is_analyzed']
    ]

    updated_clips = []
    num_analyzed = 0
    for clip in clips_to_analyze:        
        if clip['is_analyzed'] == False:
            results = analyze_clip(clip)
            clip['scores'] = results['score']
            clip['keywords'] = results['keywords']
            clip['reasoning'] = results['reasoning']
            clip['is_analyzed'] = True
            updated_clips.append(clip)
            num_analyzed += 1
        
    send_message(f'Finished analyzing {num_analyzed} clips.', discord_channel_id)

    final_clips = analyzed_clips + updated_clips

    with open(metadata_file, 'w') as f:
        json.dump(final_clips, f, indent=2)

    print('Done scoring all clips')
