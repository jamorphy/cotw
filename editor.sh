#!/bin/bash

export PATH=$PATH:/snap/bin/yq

cd /home/j/cotw

working_folder=$(yq eval '.working_folder' config.yaml)
ffmpeg_path=$(yq eval '.ffmpeg_path' config.yaml)

cd ${working_folder}

VENV_PATH="$working_folder/virtualenv"

source virtualenv/bin/activate

export PATH="$VENV_PATH/bin:$PATH"
export PATH=$PATH:$ffmpeg_path

if [ -z "$1" ]; then
    echo "Usage: $0 <game_name>"
    exit 1
fi

python editor.py "$1"

deactivate
