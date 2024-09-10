import os
import re
import yaml
import argparse
from autogen import ConversableAgent
from dotenv import load_dotenv
import autogen

from twitch import get_top_clips
from collect_and_summarize import summarize

from util import get_working_folder, generate_unique_id, get_game_info
from agents import clip_scraper, clip_summarizer

load_dotenv()

available_functions = {
    "get_top_clips": get_top_clips,
    "summarize": summarize
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

user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=5,
    code_execution_config={"work_dir": "coding", "use_docker": False},
    function_map=available_functions
)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("game_name", help="Name of game to scrape")
    args = parser.parse_args()

    with open("metadata.yaml", "r") as f:
        games = yaml.safe_load(f)["games"]    

    game_id, game_display = get_game_info(games, args.game_name)

    working_folder = get_working_folder(args.game_name)
    if working_folder:
        print(f'Active folder exists: {working_folder}')
    else:
        folder_name = f'{args.game_name}-{generate_unique_id()}'        
        try:
            os.mkdir(folder_name)
            print(f'created new folder: {folder_name}')
            working_folder = os.path.join(os.getcwd(), folder_name)
        except FileExistsError:
            print(f"Folder '{folder_name}' already exists.")
        except Exception as e:
            print(f"An error occurred while creating the folder: {e}")

    if game_id and game_display:
        single_turn.initiate_chat(
            clip_scraper,
            is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
            message=f"Let's collect some clips for {game_display.upper()} (game id: {game_id}, work_dir: {working_folder}).",
            max_turns=2
        )

        single_turn.initiate_chat(
            clip_summarizer,
            message=f"Let's summarize the clips. The working directory is {working_folder}",
            max_turns=2
        )
    else:
        print(f"Game '{args.game_name}' not found in the categories.")