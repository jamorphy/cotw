import os
import uuid

def generate_unique_id(): return str(uuid.uuid4()).replace("-", "")

def get_working_folder(game_name):
    current_dir = os.getcwd()

    for entry in os.listdir(current_dir):
        if os.path.isdir(os.path.join(current_dir, entry)):
            if entry.startswith(game_name):
                return os.path.join(current_dir, entry)
    return None

def get_game_info(metadata, game_name):
    game_info = metadata.get(game_name)
    if game_info:
        return game_info["id"], game_info["display"], game_info["min_views"]
    else:
            print(f'Game \'{game_name}\' does not exist in metadata.yaml')
            exit(1)

def get_editor_info(metadata, game_name):
    game_info = metadata.get(game_name)
    if game_info:
        return game_info["min_views"], game_info["min_runtime"]
    else:
            print(f'Game \'{game_name}\' does not exist in metadata.yaml')
            exit(1)

def get_discord_info(metadata, game_name):
    game_info = metadata.get(game_name)
    if game_info:
        return game_info["id"], game_info["display"], game_info["min_views"], game_info["min_runtime"]
    else:
            print(f'Game \'{game_name}\' does not exist in metadata.yaml')
            exit(1)