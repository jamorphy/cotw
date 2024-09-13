#!/bin/bash

working_folder="/Users/j/Workspace/videogen/"
cd ${working_folder}

VENV_PATH="$working_folder/virtualenv"

source virtualenv/bin/activate

export PATH="$VENV_PATH/bin:$PATH"
export PATH=$PATH:/opt/homebrew/bin/ffmpeg:/opt/homebrew/bin/ffmpeg

if [ -z "$1" ]; then
    echo "Usage: $0 <game_name>"
    exit 1
fi

python scrape.py "$1"

deactivate