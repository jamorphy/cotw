import os
import autogen
from dotenv import load_dotenv

load_dotenv()

scraper_config = {
    "config_list": [{"model": "gpt-4o-mini", "api_key": os.environ["OPENAI_API_KEY"], "api_type": "openai"}],
    "functions": [
        {
            "name": "get_top_clips",
            "description": "Fetches the top clips for a specific game ID on twitch",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "The Twitch game ID"},
                    "work_dir": {"type": "string", "description": "The working directory where all clips and metadata is saved."},
                    "limit": {"type": "string", "description": "Max nubmer of clips to get, default '10'"}                    
                }                
            },                    
            "required": ["game_id", "work_dir"],
        }
    ]
}

summarizer_config = {
    "config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"], "api_type": "openai"}],
    "functions": [
        {
            "name": "summarize",
            "description": "Collects the summary for all data in the clips folder",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_dir": {"type": "string", "description": "The working directory where all clips and metadata is saved."},
                }                
            },                    
            "required": ["game_id", "work_dir"],
        }
    ]
}

analysis_config = {
    "config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"], "api_type": "openai"}]
}

orchestrator_config = {
    "config_list": [{"model": "claude-3-5-sonnet-20240620", "api_key": os.environ["ANTHROPIC_API_KEY"], "api_type": "anthropic"},
                    {"model": "claude-3-opus-20240229", "api_key": os.environ["ANTHROPIC_API_KEY"], "api_type": "anthropic"}]
}

clip_scraper = autogen.AssistantAgent(
    name="ClipScraper",
    llm_config=scraper_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
    system_message="""You are an agent specialized in fetching top Twitch clips. Use the fetch_top_twitch_clips function to get clips for a specified game id. 
                    When you are finished scraping, reply with 'TERMINATE'."""
)

clip_summarizer = autogen.AssistantAgent(
    name="ClipSummarizer",
    human_input_mode="NEVER",
    llm_config=summarizer_config,
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
    system_message="""You are an agent whose job is to summarize the data collected by the clip scraper. You will collect an transcription of the audio, then provide a detailed summary of the clip based on what you collect.
                      For collecting the audio transcription, use the summarizer function which will go through every clip and save text transcriptions of the video in their respective folders.
                      
                      When you finish summarizing, reply with 'TERMINATE'."""
)

# Clip Content Analyzer
content = autogen.AssistantAgent(
    name="ContentAnalyzer",
    llm_config=orchestrator_config,
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
    human_input_mode="NEVER",
    system_message="""You are an expert in analyzing gaming content, specifically Twitch clips. Your role is to evaluate clips based on their transcription and 
                      video frame data, considering factors such as gameplay skill, entertainment value, and overall relevance. Provide detailed reasoning for 
                      your evaluations and be open to discussion with the Orchestrator and MetricsAnalyzer. Score clips on a scale of 1-10, with 10 being the highest 
                      quality."""
)

# Clip Metadata Analyzer
metrics = autogen.AssistantAgent(
    name="MetricsAnalyzer",
    llm_config=orchestrator_config,
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
    human_input_mode="NEVER",
    system_message="""You are an expert in analyzing video clip metrics. Your role is to manage the discussion with the ContentAnalyzer and the Orchestrator. 
                      When evaluating clips, your main focus should be on metrics such as view count and runtime and how they could be relevant to the compilation.
                      These metrics are important, but do not score a clip based off this alone, as there are many quality clips that may have low engagement.
                      The title of might give an indication of what happens in the video, but if it's irrelevant ignore it, the content matters more.
                      Your goal is to assign a quality score (1-10) based on how well a given clip would fit in a compilation video."""
)

# Video fit Analyzer
orchestrator = autogen.AssistantAgent(
    name="Orchestrator",
    llm_config=orchestrator_config,
    human_input_mode="NEVER",    
    system_message="""You are the orchestrator of the clip evaluation process. Your role is to manage the discussion with the Content and Metrics analyzer, considering user preferences 
                      and overall clip quality. Guide the conversation to ensure a thorough evaluation of each clip. As the orchestrator, you are to judge whether or not a clip fits the
                      user preferences of having engaging gameplay, funny moments, or overall skillfull gameplay. Aim to reach a consensus on the final score (1-10)
                      for each clip, but be prepared to make a final decision if agreement isn't reached after 5 discussion turns. Consider factors such as viewer engagement, 
                      gameplay skill, and entertainment value when evaluating clips.
                      
                      When agreement has been reached, you will output the following:
                      final_score: <insert final score whole number score here, no fraction>
                      keywords: <insert brief keywords to describe the clip>
                      reasoning: <insert brief reasoning why the score was given>
                      TERMINATE
                      """
)