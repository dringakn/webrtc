#!/bin/bash
# generate_test_video.sh
#
# This script generates a test video file using one of two methods with ffmpeg:
#
# 1. "testsrc" mode (default):
#    - Generates a test source video using ffmpeg's testsrc filter.
#    - Defaults: duration=10 seconds, size=320x240, rate=10 fps, output file test.mp4
#
# 2. "bounce" mode:
#    - Generates a bouncing image test video by overlaying an external image (default: data/ball.png)
#      on a black background.
#    - Defaults: duration=60 seconds, size=320x240, rate=10 fps, output file test.mp4, image file ball.png
#
# Options:
#   -m mode       (video type: "testsrc" (default) or "bounce")
#   -d duration   (duration in seconds; default for testsrc=10, bounce=60)
#   -s size       (resolution e.g. 320x240; default: 320x240)
#   -r rate       (frame rate in fps; default: 10)
#   -o filename   (output file name; default: test.mp4)
#   -I image      (image file for bounce mode; default: data/ball.png)
#   -F            (force overwrite output file by passing ffmpeg’s -y flag)
#   -h            (display this help/usage message)
#
# Example usage:
#   ./generate_test_video.sh -m bounce -d 60 -s 320x240 -r 10 -o test.mp4 -I ball.png -F
#
# Prerequisites:
#   - ffmpeg must be installed (e.g., sudo apt install ffmpeg).
#   - For bounce mode, the external image must exist (default is data/ball.png).

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg could not be found. Please install ffmpeg to use this script."
    exit 1
fi

# Default mode is "testsrc" or "bounce"
mode="bounce"
# Set default values for parameters.
default_duration_testsrc=10
default_duration_bounce=60
size="320x240"
rate=10
output="test.mp4"
image="data/ball.png"
force=1
duration_provided=""
# Define horizontal and vertical velocities (pixels per second) for the bouncing effect.
vx=100
vy=60

usage() {
    echo "Usage: $0 [-m mode] [-d duration] [-s size] [-r rate] [-o output_file] [-I image_file] [-F]"
    echo "    -m mode       Video type: \"testsrc\" (default) or \"bounce\""
    echo "    -d duration   Duration in seconds (default: testsrc=$default_duration_testsrc, bounce=$default_duration_bounce)"
    echo "    -s size       Resolution e.g. 320x240 (default: 320x240)"
    echo "    -r rate       Frame rate in fps (default: 10)"
    echo "    -o filename   Output file name (default: test.mp4)"
    echo "    -I image      Image file for bounce mode (default: data/ball.png)"
    echo "    -F            Force overwrite output file (ffmpeg -y)"
    exit 1
}

# Parse command-line options
while getopts "m:d:s:r:o:I:Fh" opt; do
    case ${opt} in
        m)
            mode="${OPTARG}"
            ;;
        d)
            duration_provided="${OPTARG}"
            ;;
        s)
            size="${OPTARG}"
            ;;
        r)
            rate="${OPTARG}"
            ;;
        o)
            output="${OPTARG}"
            ;;
        I)
            image="${OPTARG}"
            ;;
        F)
            force=1
            ;;
        h)
            usage
            ;;
        \?)
            usage
            ;;
    esac
done

# Set duration based on mode if not provided by user.
if [ -z "${duration_provided}" ]; then
    if [ "${mode}" == "bounce" ]; then
        duration=${default_duration_bounce}
    else
        duration=${default_duration_testsrc}
    fi
else
    duration="${duration_provided}"
fi

# Create the data directory (inside the tests folder) if it doesn't exist.
mkdir -p data

# Define the force flag for ffmpeg.
if [ ${force} -eq 1 ]; then
    force_flag="-y"
else
    force_flag=""
fi

if [ "${mode}" == "bounce" ]; then
    # Check if the image file exists.
    if [ ! -f "${image}" ]; then
        echo "Image file '${image}' not found!"
        exit 1
    fi

    # Calculate the bouncing trajectory using ffmpeg's overlay filter.
    filter="overlay=x='if(lte(mod(t*${vx},2*(main_w-overlay_w)),(main_w-overlay_w)),mod(t*${vx},2*(main_w-overlay_w)),2*(main_w-overlay_w)-mod(t*${vx},2*(main_w-overlay_w)))':y='if(lte(mod(t*${vy},2*(main_h-overlay_h)),(main_h-overlay_h)),mod(t*${vy},2*(main_h-overlay_h)),2*(main_h-overlay_h)-mod(t*${vy},2*(main_h-overlay_h)))'"

    echo "Generating bouncing image test video..."
    ffmpeg ${force_flag} -f lavfi -i "color=c=black:s=${size}:d=${duration}:r=${rate}" \
           -i "${image}" \
           -filter_complex "${filter}" \
           "data/${output}"
else
    echo "Generating testsrc video..."
    ffmpeg ${force_flag} -f lavfi -i "testsrc=duration=${duration}:size=${size}:rate=${rate}" \
           "data/${output}"
fi
