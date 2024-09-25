###
### collection.py
###
### Collects and summarizes data from scraper

import os
import io
from openai import OpenAI
from anthropic import Anthropic
import base64
import json
import cv2
from PIL import Image

def summarize(work_dir):
    metadata_path = os.path.join(work_dir, 'clips_metadata.json')

    oai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # TODO fix this
    older_clips = [clip for clip in metadata if clip['is_analyzed'] == True]
    newer_clips = [clip for clip in metadata if clip['is_analyzed'] == False]

    print(f"There are {len(older_clips)} older clips and {len(newer_clips)} newer clips to summarize.")
    
    updated_clips = []
    for clip in newer_clips:
        # TODO: Uncomment
        #transcription = transcribe_audio(oai_client, clip['audio_path'])
        clip['transcription'] = "This is a dummy transcription."
        frames = ["frame1", "frame2", "frame3"]
        #frames = extract_frames(clip['video_path'])

        if clip['transcription'] and frames:
            #summary = get_summary(anthropic_client, transcription, frames)
            clip['summary'] = "This is a testing summary, give this clip a 5/10."

        updated_clips.append(clip)

    final_clips = older_clips + updated_clips
    
    with open(os.path.join(work_dir, 'clips_metadata.json'), 'w') as f:
        json.dump(final_clips, f, indent=2)

    return f"Finished summarizing {len(updated_clips)} clips."

def extract_frames(file_path, num_frames=8, compression_quality=40):
    print(f'Currently extracting frames from {file_path}')

    try:
        # Open the video file
        cap = cv2.VideoCapture(file_path)

        # Get the total number of frames
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate the step size to extract evenly spaced frames
        step = total_frames // (num_frames - 1)

        # Initialize a list to store the compressed frames
        compressed_frames = []

        # Iterate through the frames and extract the desired ones
        for i in range(num_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            ret, frame = cap.read()
            if ret:
                # Convert the frame to PIL Image format
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                # Create a BytesIO object to store the compressed image
                compressed_image = io.BytesIO()

                # Save the image to the BytesIO object with compression
                pil_image.save(compressed_image, format='JPEG', quality=compression_quality)
                compressed_image_data = base64.b64encode(compressed_image.getvalue()).decode('utf-8')

                # Get the compressed image data from the BytesIO object
                compressed_frames.append(compressed_image_data)

        cap.release()

        return compressed_frames

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def transcribe_audio(client, file_path):
    print(f'Now transcribing: {file_path}')
    try:
        with open(file_path, "rb") as mp3:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=mp3
            )
        if transcription:
            return transcription.text
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def get_summary(client, transcription, compressed_frames):

    def create_message_with_images(compressed_frames):
        content = []
        
        for i, frame_data in enumerate(compressed_frames, 1):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": frame_data,
                },
            })        

        content.append({
            "type": "text",
            "text": f"Transcription: {transcription}"
        })
        
        return content
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=3000,
        system="""
                  You are a gaming clip summarizer. Given frames and an audio transcription of a clip,
                  give a highly detailed summary of what happens in the clip from start to finish.

                  Describe what you see in the clip.
                  
                  Make sure to note if there are any standout moments in the clip that are 'clip worthy'.
                  RETURN YOUR RESPONSE IN PLAIN TEXT ONLY.
                  """,
        messages=[
            {
                "role": "user",
                "content": create_message_with_images(compressed_frames),
            }
        ],
    )

    return message.content[0].text