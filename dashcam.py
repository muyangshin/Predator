# Predator

# Copyright (C) 2024 V0LT - Conner Vieira 

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License along with this program (LICENSE)
# If not, see https://www.gnu.org/licenses/ to read the license agreement.



import os # Required to interact with certain operating system functions
import json # Required to process JSON data

predator_root_directory = str(os.path.dirname(os.path.realpath(__file__))) # This variable determines the folder path of the root Predator directory. This should usually automatically recognize itself, but it if it doesn't, you can change it manually.

try:
    if (os.path.exists(predator_root_directory + "/config.json")):
        config = json.load(open(predator_root_directory + "/config.json")) # Load the configuration database from config.json
    else:
        print("The configuration file doesn't appear to exist at " + predator_root_directory + "/config.json.")
        exit()
except:
    print("The configuration database couldn't be loaded. It may be corrupted.")
    exit()


import utils
display_message = utils.display_message
debug_message = utils.debug_message
process_timing = utils.process_timing
get_gps_location = utils.get_gps_location
heartbeat = utils.heartbeat
update_state = utils.update_state
convert_speed = utils.convert_speed

import threading
import time
import cv2
import subprocess # Required for starting some shell commands
import sys
import datetime # Required for converting between timestamps and human readable date/time information
if (config["general"]["gps"]["enabled"] == True): # Only import the GPS libraries if GPS settings are enabled.
    from gps import * # Required to access GPS information.
    import gpsd
if (config["dashcam"]["saving"]["looped_recording"]["mode"] == "automatic"): # Only import the disk usage library if it is enabled in the configuration.
    import psutil # Required to get disk usage information

if (config["dashcam"]["notifications"]["reticulum"]["enabled"] == True): # Check to see if Reticulum notifications are enabled.
    import reticulum



if (config["dashcam"]["saving"]["looped_recording"]["mode"] == "manual"): # Only validate the manual history length if manual looped recording mode is enabled.
    if (int(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"]) != float(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"])): # Check to see if the dashcam unsaved history length is not a whole number.
        display_message("The 'dashcam>saving>looped_recording>manual>history_length' setting doesn't appear to be an integer. This value has been rounded to the nearest whole number.", 3)
        config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"] = round(float(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"])) # Found the dashcam history length off to a whole number.
    elif (type(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"]) != int): # Check to see if the dashcam history length is not an integer.
        display_message("The 'dashcam>saving>looped_recording>manual>history_length' setting doesn't appear to be an integer, but it is a whole number. Make sure this configuration value does not have a decimal point.", 2)
    if (int(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"]) < 0): # Check to see if the dashcam history length is a negative number.
        display_message("The 'dashcam>saving>looped_recording>manual>history_length' setting appears to be a negative number. This value has been defaulted to 0, which is likely to cause unexpected behavior.", 3)
        config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"] = 0 # Default the dashcam history length to 0, even though this is likely to cause unexpected behavior.
    elif (int(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"]) < 2): # Check to see if the dashcam history length is less than 2.
        display_message("The 'dashcam>saving>looped_recording>manual>history_length' setting appears to be a number that is less than 2. This is likely to cause unexpected behavior.", 2)
elif (config["dashcam"]["saving"]["looped_recording"]["mode"] == "automatic"): # Only validate the automatic looped recording configuration values if automatic looped recording mode is enabled.
    if (type(config["dashcam"]["saving"]["looped_recording"]["automatic"]["minimum_free_percentage"]) != float):
        display_message("The 'dashcam>saving>looped_recording>automatic>minimum_free_percentage' setting is not a floating point number.", 2)
    if (config["dashcam"]["saving"]["looped_recording"]["automatic"]["minimum_free_percentage"] < 0):
        display_message("The 'dashcam>saving>looped_recording>automatic>minimum_free_percentage' value is a negative number.", 3)
    elif (config["dashcam"]["saving"]["looped_recording"]["automatic"]["minimum_free_percentage"] > 1):
        display_message("The 'dashcam>saving>looped_recording>automatic>minimum_free_percentage' value is greater than 1 (or 100%).", 3)
    elif (config["dashcam"]["saving"]["looped_recording"]["automatic"]["minimum_free_percentage"] >= 0.99):
        display_message("The 'dashcam>saving>looped_recording>automatic>minimum_free_percentage' value is greater than or equal to 0.99 (or 99%). This is exceedingly high, and may cause Predator to run out of disk space in between segments.", 2)
    elif (config["dashcam"]["saving"]["looped_recording"]["automatic"]["minimum_free_percentage"] <= 0.05):
        display_message("The 'dashcam>saving>looped_recording>automatic>minimum_free_percentage' value is less than or equal to 0.05 (or 5%). This is exceedingly low, and may cause issues if Predator is unable to reach the minimum free disk space threshold by only erasing dashcam segments.", 2)

    if (type(config["dashcam"]["saving"]["looped_recording"]["automatic"]["max_deletions_per_round"]) != int):
        config["dashcam"]["saving"]["looped_recording"]["automatic"]["max_deletions_per_round"] = int(round(config["dashcam"]["saving"]["looped_recording"]["automatic"]["max_deletions_per_round"]))
        display_message("The 'dashcam>saving>looped_recording>automatic>max_deletions_per_round' setting is not an integer number. This value has been temporarily rounded to the nearest whole number.", 2)
    if (config["dashcam"]["saving"]["looped_recording"]["automatic"]["max_deletions_per_round"] < 0):
        display_message("The 'dashcam>saving>looped_recording>automatic>max_deletions_per_round' setting is a negative number. This will prevent Predator from ever erasing old dash-cam segments.", 3)
    elif (config["dashcam"]["saving"]["looped_recording"]["automatic"]["max_deletions_per_round"] < 2):
        display_message("The 'dashcam>saving>looped_recording>automatic>max_deletions_per_round' setting is less than 2. This is likely to cause unexpected behavior.", 2)

if (config["dashcam"]["parked"]["enabled"] == True): # Only validate the parking mode configuration values if parking mode is enabled.
    if (config["general"]["gps"]["enabled"] == False):
        display_message("Dash-cam parking mode is enabled, but GPS functionality is disabled. Parking mode needs GPS information to determine when the vehicle is stopped. Without it, Predator will enter parking mode as soon as the threshold time is reached, and it will never return to normal recording mode.", 2)
    if (config["dashcam"]["parked"]["conditions"]["speed"] < 0):
        display_message("The 'dashcam>parked>conditions>speed' setting is a negative number. This will prevent Predator from ever entering parked mode. To prevent unexpected behavior, you should set 'dashcam>parked>enabled' to 'false'.", 2)

    if (config["dashcam"]["parked"]["recording"]["sensitivity"] < 0):
        display_message("The 'dashcam>parked>recording>sensitivity' setting is a negative number. This will cause unexpected behavior.", 3)
    elif (config["dashcam"]["parked"]["recording"]["sensitivity"] > 0.9):
        display_message("The 'dashcam>parked>recording>sensitivity' setting is an exceedingly high value (above 90%). This will likely cause unexpected behavior.", 2)
    elif (config["dashcam"]["parked"]["recording"]["sensitivity"] > 1):
        display_message("The 'dashcam>parked>recording>sensitivity' setting is above 100%. This will effectively prevent Predator from ever detecting motion.", 2)




def merge_audio_video(video_file, audio_file, output_file, audio_offset=0):
    debug_message("Merging audio and video files")

    merge_command = "ffmpeg -i " + audio_file + " -itsoffset -" + str(audio_offset) + " -i " + video_file + " -c copy " + output_file
    erase_command = "timeout 1 rm " + video_file + " " + audio_file

    merge_process = subprocess.run(merge_command.split(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    first_attempt = utils.get_time()
    while (merge_process.returncode != 0): # If the merge process exited with an error, keep trying until it is successful. This might happen if one of the files hasn't fully saved to disk.
        merge_process = subprocess.run(merge_command.split(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if (utils.get_time() - first_attempt > 5): # Check to see if FFMPEG has been trying for at least 5 seconds.
            display_message("The audio and video segments could not be merged. It is possible one or both of the files is damaged.", 2)
            process_timing("end", "Dashcam/File Merging")
            return False # Time out, and exit with a success value False.
    subprocess.run(erase_command.split())

    debug_message("Merged audio and video files")
    return True



def benchmark_camera_framerate(device, frames=5): # This function benchmarks a given camera to determine its framerate.
    global config

    resolution = [config["dashcam"]["capture"]["video"]["resolution"]["width"], config["dashcam"]["capture"]["video"]["resolution"]["height"]] # This determines the resolution that will be used for the video capture device.
    capture = cv2.VideoCapture(config["dashcam"]["capture"]["video"]["devices"][device]["index"]); # Open the video capture device.
    codec = list(config["dashcam"]["capture"]["video"]["devices"][device]["codec"])
    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(codec[0], codec[1], codec[2], codec[3])) # Set the video codec.
    capture.set(cv2.CAP_PROP_FPS, 120) # Set the frame-rate to a high value so OpenCV will use the highest frame-rate the capture supports.

    capture.set(cv2.CAP_PROP_FRAME_WIDTH,resolution[0]) # Set the video stream width.
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT,resolution[1]) # Set the video stream height.
    if (capture is None or capture.isOpened() == False): # Check to see if the capture failed to open.
        display_message("Failed to open video capture on device '" + str(device) + "' for frame-rate benchmarking.", 3)

    debug_message("Running benchmark for '" + device + "'...")

    for i in range(0, 10): # Loop a few times to allow the camera to warm up before the benchmark starts.
        ret, frame = capture.read() # Capture a video frame.
        if (config["dashcam"]["capture"]["video"]["devices"][device]["flip"]): # Check to see if Predator is convered to flip this capture device's output.
            frame = cv2.rotate(frame, cv2.ROTATE_180) # Flip the frame by 180 degrees.
    start_time = utils.get_time() # Record the exact time that the benchmark started.
    for i in range(0, frames): # Run until the specified number of frames have been captured.
        ret, frame = capture.read() # Capture a video frame.
        frame = apply_dashcam_stamps(frame) # Apply dashcam overlay stamps to the frame.
        if (config["dashcam"]["capture"]["video"]["devices"][device]["flip"]): # Check to see if Predator is convered to flip this capture device's output.
            frame = cv2.rotate(frame, cv2.ROTATE_180) # Flip the frame by 180 degrees.

    end_time = utils.get_time() # Record the exact time that the benchmark ended.
    total_time = end_time - start_time # Calculate how many seconds the benchmark took to complete.
    fps = frames / total_time # Calculate the number of frames captured per second.
    debug_message("Capture device '" + device + "' runs at " + str(round(fps*10)/10) + "fps")

    return fps # Return the calculated FPS.






# This function is called when the lock trigger file is created, usually to save the current and last segments.
segments_saved_time = {} # This is a dictionary that holds a list of the dashcam segments that have been saved, and the time that they were saved.
def save_dashcam_segments(file1, file2=""):
    global config
    global segments_saved_time
    process_timing("start", "Dashcam/File Maintenance")
    cooldown = 0.5 # This is how long Predator will wait to allow other threads to detect the lock trigger file. This also determines how long the user has to wait before saving the same file again.

    anything_saved = False # This will be changed to 'True' is one or more files is saved.
    if (os.path.isdir(config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"]) == False): # Check to see if the saved dashcam video folder needs to be created.
        os.system("mkdir -p '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Create the saved dashcam video directory.
    if (os.path.isdir(config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"])): # Check to see if the dashcam saving directory exists.
        if (file1 in segments_saved_time): # Check to see if file 1 has been saved previously.
            if (utils.get_time() - segments_saved_time[file1] > cooldown): # Check to see if a certain amount of time has passed since this segment was last saved before saving it again.
                os.system("cp '" + file1 + "' '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Copy the current dashcam video segment to the saved folder.
                segments_saved_time[file1] = utils.get_time()
                anything_saved = True # Indicate that at least one file was saved.
        else: # If file 1 hasn't been saved previously, then save it.
            os.system("cp '" + file1 + "' '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Copy the current dashcam video segment to the saved folder.
            segments_saved_time[file1] = utils.get_time()
            anything_saved = True # Indicate that at least one file was saved.
        if (file2 != ""): # Check to see if there is a second file to copy.
            if (file2 in segments_saved_time): # Check to see if file 2 has been saved previously.
                if (utils.get_time() - segments_saved_time[file2] > cooldown): # Check to see if a certain amount of time has passed since this segment was last saved before saving it again.
                    os.system("cp '" + file2 + "' '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Copy the last dashcam video segment to the saved folder.
                    segments_saved_time[file2] = utils.get_time()
                    anything_saved = True # Indicate that at least one file was saved.
            else: # If file 2 hasn't been saved previously, then save it.
                os.system("cp '" + file2 + "' '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Copy the last dashcam video segment to the saved folder.
                segments_saved_time[file2] = utils.get_time()
                anything_saved = True # Indicate that at least one file was saved.
    else:
        display_message("The dashcam saving directory does not exist, and could not be created. The dashcam video could not be locked.", 3)

    if (anything_saved == True): # Check to see if anything was saved before displaying the dashcam save notice.
        display_message("Saved the current dashcam segment.", 1)

    time.sleep(0.3) # Wait for a short period of time so that other dashcam recording threads have time to detect the trigger file.
    os.system("rm -rf '" + config["general"]["interface_directory"] + "/" + config["dashcam"]["saving"]["trigger"] + "'") # Remove the dashcam lock trigger file.
    if (os.path.exists(config["general"]["interface_directory"] + "/" + config["dashcam"]["saving"]["trigger"])): # Check to see if the trigger file exists even after it should have been removed.
        display_message("Unable to remove dashcam lock trigger file.", 3)

    process_timing("end", "Dashcam/File Maintenance")




def apply_dashcam_stamps(frame):
    process_timing("start", "Dashcam/Apply Stamps")
    try:
        height, width, channels = frame.shape
    except:
        display_message("Failed to determine frame size while applying overlay stamps. It is likely something has gone wrong with video capture.", 3)

    main_stamp_position = [10, height - 10] # Determine where the main overlay stamp should be positioned in the video stream.
    main_stamp = ""
    if (config["dashcam"]["stamps"]["main"]["unix_time"]["enabled"] == True): # Check to see if the Unix epoch time stamp is enabled.
        main_stamp = main_stamp + str(round(utils.get_time())) + " " # Add the current Unix epoch time to the main stamp.
    if (config["dashcam"]["stamps"]["main"]["date"]["enabled"] == True): # Check to see if the date stamp is enabled.
        main_stamp = main_stamp + str(datetime.datetime.fromtimestamp(utils.get_time()).strftime("%Y-%m-%d")) + " "  # Add the date to the main stamp.
    if (config["dashcam"]["stamps"]["main"]["time"]["enabled"] == True): # Check to see if the time stamp is enabled.
        main_stamp = main_stamp + str(datetime.datetime.fromtimestamp(utils.get_time()).strftime("%H:%M:%S")) + " "  # Add the time to the main stamp.
    main_stamp = main_stamp  + "  " + config["dashcam"]["stamps"]["main"]["message_1"] + "  " + config["dashcam"]["stamps"]["main"]["message_2"] # Add the customizable messages to the overlay stamp.

    gps_stamp_position = [10, 30] # Determine where the GPS overlay stamp should be positioned in the video stream.
    gps_stamp = "" # Set the GPS to a blank placeholder. Elements will be added to this in the next steps.
    if (config["general"]["gps"]["enabled"] == True): # Check to see if GPS features are enabled before processing the GPS stamp.
        current_location = get_gps_location() # Get the current location.
        
        if (config["dashcam"]["stamps"]["gps"]["location"]["enabled"] == True): # Check to see if the GPS location stamp is enabled.
            gps_stamp = gps_stamp + "(" + str(f'{current_location[0]:.5f}') + ", " + str(f'{current_location[1]:.5f}') + ")  " # Add the current coordinates to the GPS stamp.
        if (config["dashcam"]["stamps"]["gps"]["altitude"]["enabled"] == True): # Check to see if the GPS altitude stamp is enabled.
            gps_stamp = gps_stamp + str(round(current_location[3])) + "m  " # Add the current altitude to the GPS stamp.
        if (config["dashcam"]["stamps"]["gps"]["speed"]["enabled"] == True): # Check to see if the GPS speed stamp is enabled.
            gps_stamp = gps_stamp + str(round(convert_speed(current_location[2],config["dashcam"]["stamps"]["gps"]["speed"]["unit"])*10)/10) + config["dashcam"]["stamps"]["gps"]["speed"]["unit"] + "  " # Add the current speed to the GPS stamp.

    # Determine the font color of the stamps from the configuration.
    main_stamp_color = config["dashcam"]["stamps"]["main"]["color"]
    gps_stamp_color = config["dashcam"]["stamps"]["gps"]["color"]

    # Add the stamps to the video stream.
    cv2.putText(frame, main_stamp, (main_stamp_position[0], main_stamp_position[1]), 2, config["dashcam"]["stamps"]["size"], (main_stamp_color[2], main_stamp_color[1], main_stamp_color[0])) # Add the main overlay stamp to the video stream.
    cv2.putText(frame, gps_stamp, (gps_stamp_position[0], gps_stamp_position[1]), 2, config["dashcam"]["stamps"]["size"], (gps_stamp_color[2], gps_stamp_color[1], gps_stamp_color[0])) # Add the GPS overlay stamp to the video stream.

    process_timing("end", "Dashcam/Apply Stamps")
    return frame





def detect_motion(frame, background_subtractor):
    process_timing("start", "Dashcam/Detection Motion")
    frame_height, frame_width, channels = frame.shape
    total_image_area = frame_height * frame_width

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    fgmask = background_subtractor.apply(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fgmask = cv2.erode(fgmask, kernel, iterations=1)
    fgmask = cv2.dilate(fgmask, kernel, iterations=1)
    contours, hierarchy = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    filtered_contours = [] # This is a placeholder that will hold the list of filtered motion detection contours.

    moving_area = 0 # This value will hold the number of pixels in the image that are moving.
    for contour in contours: # Iterate through each contour.
        x, y, w, h = cv2.boundingRect(contour) # Define the edges of the contour.
        width_percentage = (w / frame_width)
        height_percentage = (h / frame_height)

        if (width_percentage < 0.95 and height_percentage < 0.95): # Check to make sure this movement contour doesn't cover the entire screen.
            moving_area += cv2.contourArea(contour) # Increment the moving_area counter by the number of pixels in the contour.
            filtered_contours.append(contour)



    moving_percentage = moving_area / total_image_area # Calculate the percentage of the frame that is in motion.
    moving_percentage_human = "{:.5f}%".format(moving_percentage*100) # Convert the moving percentage to a human-readable string.

    process_timing("end", "Dashcam/Detection Motion")
    return filtered_contours, moving_percentage





# This function is called as a subprocess of the normal dashcam recording, and is triggered when motion is detected. This function exits when motion is no longer detected (after the motion detection timeout).
instant_framerate = {} # This will hold the instantaneous frame-rate of each device, which is calculated based on the time between the two most recent frames. This value is expected to flucuate significantly.
def record_parked_motion(capture, framerate, width, height, device, directory, frame_history):
    global instant_framerate
    global parked
    global config
    last_motion_detected = utils.get_time() # Initialize the last time that motion was detected to now. We can assume motion was just detected because this function is only called after motion is detected.

    file_name = directory + "/predator_dashcam_" + str(round(utils.get_time())) + "_" + str(device) + "_0_P"
    video_file_name = file_name + ".avi"
    audio_file_name = file_name + "." + str(config["dashcam"]["capture"]["audio"]["extension"])
    if (framerate > float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"])): # Check to see if the frame-rate benchmark results exceed the maximum allowed frame-rate.
        framerate = float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"]) # Set the frame-rate to the maximum allowed frame-rate.
    output = cv2.VideoWriter(video_file_name, cv2.VideoWriter_fourcc(*'XVID'), float(framerate), (width,  height))

    process_timing("start", "Dashcam/Detection Motion")
    background_subtractor = cv2.createBackgroundSubtractorMOG2() # Initialize the background subtractor for motion detection.
    process_timing("end", "Dashcam/Detection Motion")
    if (config["dashcam"]["capture"]["audio"]["enabled"] == True):
        audio_recorder = subprocess.Popen(["arecord", "-q", "--format=cd", audio_file_name], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) # Start the audio recorder for the parked segment.

    audio_offset = len(frame_history) / framerate
    process_timing("start", "Dashcam/Writing")
    for frame in frame_history: # Iterate through each frame in the frame history.
        output.write(frame) # Save this frame to the video.
    process_timing("end", "Dashcam/Writing")


    frames_captured = 0 # This is a placeholder that will keep track of how many frames are captured in this parked recording.
    capture_start_time = utils.get_time() # This stores the time that this parked recording started.
    last_frame_captured = time.time() # This will hold the exact time that the last frame was captured. Here, the value is initialized to the current time before any frames have been captured.

    process_timing("start", "Dashcam/Calculations")
    last_alert_minimum_framerate_time = 0 # This value holds the last time a minimum frame-rate alert was displayed. Here the value is initialized.
    if (float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["min"]) == 0): # Check to see if the minimum frame-rate is 0.
        expected_time_since_last_frame_slowest = 100 # Default to an arbitrarily high expected slowest frame-rate.
    else:
        expected_time_since_last_frame_slowest = 1/float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["min"]) # Calculate the longest expected time between two frames.
    expected_time_since_last_frame_fastest = 1/float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"]) # Calculate the shortest expected time between two frames.
    process_timing("end", "Dashcam/Calculations")

    while (utils.get_time() - last_motion_detected < config["dashcam"]["parked"]["recording"]["timeout"] and parked == True): # Run until motion is not detected for a certain period of time.
        heartbeat() # Issue a status heartbeat.
        update_state("dashcam/parked_active", instant_framerate)

        if (capture is None or capture.isOpened() == False): # Check to see if the capture failed to open.
            display_message("The video capture on device '" + str(device) + "' was dropped during parked recording", 3)

        time_since_last_frame = time.time()-last_frame_captured # Calculate the time (in seconds) since the last frame was captured.
        instant_framerate[device] = 1/time_since_last_frame
        if (time_since_last_frame > expected_time_since_last_frame_slowest): # Check see if the current frame-rate is below the minimum expected frame-rate.
            if (frames_captured > 1): # Check to make sure we aren't at the very beginning of recording, where frame-rate might be inconsistent.
                if (time.time() - last_alert_minimum_framerate_time > 1): # Check to see if at least 1 second has passed since the last minimum frame-rate alert.
                    display_message("The framerate on '" + device + "' (" + str(round((1/time_since_last_frame)*100)/100) + "fps) has fallen below the minimum frame-rate.", 2)
                last_alert_minimum_framerate_time = time.time() # Record the current time as the time that the last minimum frame-rate alert was shown.
        elif (time_since_last_frame < expected_time_since_last_frame_fastest): # Check see if the current frame-rate is above the maximum expected frame-rate.
            time.sleep(expected_time_since_last_frame_fastest - time_since_last_frame) # Wait to force the frame-rate to stay below the maximum limit.
        last_frame_captured = time.time() # Update the time that the last frame was captured immediately before capturing the next frame.
        ret, frame = capture.read() # Capture a frame.
        last_frame_captured = time.time() # Update the time that the last frame was captured.
        frames_captured+=1 # Increment the frame counter.

        process_timing("start", "Dashcam/Image Manipulation")
        if (config["dashcam"]["capture"]["video"]["devices"][device]["flip"]): # Check to see if Predator is convered to flip this capture device's output.
            frame = cv2.rotate(frame, cv2.ROTATE_180) # Flip the frame by 180 degrees.
        process_timing("end", "Dashcam/Image Manipulation")

        process_timing("start", "Dashcam/Motion Detection")
        contours, moving_percentage = detect_motion(frame, background_subtractor) # Run motion analysis on this frame.

        if (moving_percentage > float(config["dashcam"]["parked"]["recording"]["sensitivity"]) * 0.8): # Check to see if there is movement that exceeds 80% of the sensitivity threshold. This ensures that motion that is just barely over the threshold doesn't cause Predator to repeatedly start and stop recording.
            last_motion_detected = utils.get_time()
            if (utils.get_time() - last_motion_detected > 2): # Check to see if it has been more than 2 seconds since motion was last detected so that the message is only displayed after there hasn't been motion for some time.
                display_message("Detected motion.", 1)

        if (config["dashcam"]["parked"]["recording"]["highlight_motion"]["enabled"] == True):
            for contour in contours: # Iterate through each contour.
                if cv2.contourArea(contour) > 1: # Check to see if this contour is big enough to be worth highlighting.
                    color = config["dashcam"]["parked"]["recording"]["highlight_motion"]["color"]
                    x, y, w, h = cv2.boundingRect(contour) # Define the edges of the contour.
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (color[2], color[1], color[0]), 2) # Draw a box around the contour in the frame.

        process_timing("end", "Dashcam/Motion Detection")

        frame = apply_dashcam_stamps(frame) # Apply dashcam overlay stamps to the frame.

        process_timing("start", "Dashcam/Writing")
        frame_write_thread = threading.Thread(target=write_frame, args=[frame, output], name="FrameWrite")
        frame_write_thread.start()
        process_timing("end", "Dashcam/Writing")

    output = None # Release the video writer.

    if (config["dashcam"]["capture"]["audio"]["enabled"] == True):
        process_timing("start", "Dashcam/Audio Processing")
        audio_recorder.terminate() # Kill the active audio recorder.
        process_timing("end", "Dashcam/Audio Processing")
    process_timing("start", "Dashcam/Calculations")
    calculated_framerate = frames_captured / (utils.get_time() - capture_start_time) # Calculate the rate at which frames were captured during this recording.
    process_timing("end", "Dashcam/Calculations")
    display_message("Stopped motion recording.", 1)


    process_timing("start", "Dashcam/File Merging")
    if (config["dashcam"]["capture"]["audio"]["merge"] == True and config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if Predator is configured to merge audio and video files.
        merged_file_name = file_name + ".mkv"
        if (os.path.exists(audio_file_name) == False):
            display_message("The audio file was missing during audio/video merging at the end of parked motion recording. It is possible something has gone wrong with recording.", 2)
        else:
            audio_video_merge = threading.Thread(target=merge_audio_video, args=[video_file_name, audio_file_name, merged_file_name], name="AudioVideoMerge") # Create the thread to merge the audio and video files.
            audio_video_merge.start() # Start the merging thread.
    process_timing("end", "Dashcam/File Merging")

    return calculated_framerate


def delete_old_segments():
    global config

    process_timing("start", "Dashcam/File Maintenance")

    dashcam_files_list_command = "ls " + config["general"]["working_directory"] + " | grep predator_dashcam" # Set up the command to get a list of all unsaved dashcam videos in the working directory.
    dashcam_files = str(os.popen(dashcam_files_list_command).read())[:-1].splitlines() # Run the command, and record the raw output string.
    dashcam_files = sorted(dashcam_files) # Sort the dashcam files alphabetically to get them in chronological order (oldest first).

    if (config["dashcam"]["saving"]["looped_recording"]["mode"] == "manual"): # Check to see if looped recording is in manual mode.
        if (len(dashcam_files) > int(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"])): # Check to see if the current number of dashcam segments in the working directory is higher than the configured history length.
            videos_to_delete = dashcam_files[0:len(dashcam_files) - int(config["dashcam"]["saving"]["looped_recording"]["manual"]["history_length"])] # Create a list of all of the videos that need to be deleted.
            for video in videos_to_delete: # Iterate through each video that needs to be deleted.
                os.system("timeout 5 rm '" + config["general"]["working_directory"] + "/" + video + "'") # Delete the dashcam segment.
    elif (config["dashcam"]["saving"]["looped_recording"]["mode"] == "automatic"): # Check to see if looped recording is in automatic mode.
        free_disk_percentage = psutil.disk_usage(path=config["general"]["working_directory"]).free / psutil.disk_usage(path=config["general"]["working_directory"]).total # Calculate the initial free disk percentage.
        videos_deleted_this_round = 0 # This is a placeholder that will be incremented for each video deleted in the following step.
        while free_disk_percentage < float(config["dashcam"]["saving"]["looped_recording"]["automatic"]["minimum_free_percentage"]): # Run until the free disk percentage is lower than the configured minimum.
            if (len(dashcam_files) - videos_deleted_this_round <= 1): # Check to see if there is one or fewer total dashcam videos.
                display_message("The minimum free disk space hasn't been reached, but there are no more dashcam segments that can be deleted. You should try to free up space on the storage device, or decrease the minimum free disk space percentage in the configuration.", 2)
                break
            if (videos_deleted_this_round > config["dashcam"]["saving"]["looped_recording"]["automatic"]["max_deletions_per_round"]): # Check to see if the maximum allowed deletions per round have been reached.
                display_message("The maximum number of segments that can be deleted per round have been erased by looped recording. It is possible something has gone wrong with the disk usage analysis, or you recently increased the maximum free disk space percentage.", 2)
                break # Exit the loop
            os.system("timeout 5 rm '" + config["general"]["working_directory"] + "/" + dashcam_files[videos_deleted_this_round] + "'") # Delete the oldest remaining segment.
            free_disk_percentage = psutil.disk_usage(path=config["general"]["working_directory"]).free / psutil.disk_usage(path=config["general"]["working_directory"]).total # Recalculate the free disk percentage.
            videos_deleted_this_round += 1
    elif (config["dashcam"]["saving"]["looped_recording"]["mode"] == "disabled"): # Check to see if looped recording is disabled.
        pass
    else:
        display_message("The 'dashcam>saving>looped_recording>mode' configuration value is invalid. Looped recording is disabled.", 3)

    process_timing("end", "Dashcam/File Maintenance")






dashcam_recording_active = False
first_segment_started_time = 0
def capture_dashcam_video(directory, device="main", width=1280, height=720):
    global dashcam_recording_active
    global first_segment_started_time 
    global instant_framerate
    global parked

    device_id = config["dashcam"]["capture"]["video"]["devices"][device]["index"]

    if (os.path.isdir(config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"]) == False): # Check to see if the saved dashcam video folder needs to be created.
        os.system("mkdir -p '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Create the saved dashcam video directory.

    framerate = benchmark_camera_framerate(device) # Benchmark this capture device to determine its operating framerate.
    process_timing("start", "Dashcam/Calculations")
    if (framerate > float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"])): # Check to see if the frame-rate benchmark results exceed the maximum allowed frame-rate.
        framerate = float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"]) # Set the frame-rate to the maximum allowed frame-rate.
    process_timing("end", "Dashcam/Calculations")

    debug_message("Opening video stream on '" + device + "'")

    process_timing("start", "Dashcam/Capture Management")
    capture = cv2.VideoCapture(device_id) # Open the video stream.
    codec = list(config["dashcam"]["capture"]["video"]["devices"][device]["codec"])
    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(codec[0], codec[1], codec[2], codec[3])) # Set the video codec.
    capture.set(cv2.CAP_PROP_FPS, 120) # Set the frame-rate to a high value so OpenCV will use the highest frame-rate the capture supports.

    capture.set(cv2.CAP_PROP_FRAME_WIDTH,width) # Set the video stream width.
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT,height) # Set the video stream height.
    process_timing("end", "Dashcam/Capture Management")

    process_timing("start", "Dashcam/Motion Detection")
    background_subtractor = cv2.createBackgroundSubtractorMOG2() # Initialize the background subtractor for motion detection.
    last_motion_detection = 0 # This will hold the timestamp of the last time motion was detected.
    process_timing("end", "Dashcam/Motion Detection")

    process_timing("start", "Dashcam/Calculations")
    segment_number = 0 # This variable keeps track of the segment number, and will be incremented each time a new segment is started.
    segment_start_time = utils.get_time() # This variable keeps track of when the current segment was started. It will be reset each time a new segment is started.
    if (first_segment_started_time == 0): # Check to see if the first segment start time hasn't yet been updated. Since this is a global variable, another dashcam thread may have already set it.
        first_segment_started_time = utils.get_time() # This variable keeps track of when the first segment was started.
    frames_since_last_segment = 0 # This will count the number of frames in this video segment.

    frames_captured = 0
    process_timing("end", "Dashcam/Calculations")

    previously_parked = False # This will be used to keep track of whether or not Predator was in parked mode during the previous loop.

    process_timing("start", "Dashcam/Writing")
    file_name = directory + "/predator_dashcam_" + str(round(first_segment_started_time)) + "_" + str(device) + "_" + str(segment_number) + "_N"
    video_filepath = file_name + ".avi" # Determine the initial video file path.
    audio_filepath = file_name + "." + str(config["dashcam"]["capture"]["audio"]["extension"]) # Determine the initial audio file path.
    if (config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if audio recording is enabled in the configuration.
        audio_recorder = subprocess.Popen(["arecord", "-q", "--format=cd", file_name + "." + str(config["dashcam"]["capture"]["audio"]["extension"])], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) # Start the next segment's audio recorder.
    last_video_filepath = "" # Initialize the path of the last video file to just be a blank string.
    last_audio_filepath = "" # Initialize the path of the last audio file to just be a blank string.
    last_filename = "" # Initialize the path of the last base filename to just be a blank string.

    frame_history = [] # This will hold the last several frames in a buffer.
    output = cv2.VideoWriter(video_filepath, cv2.VideoWriter_fourcc(*'XVID'), float(framerate), (width,  height))
    process_timing("end", "Dashcam/Writing")

    if (capture is None or not capture.isOpened()):
        display_message("Failed to start dashcam video capture using '" + device  + "' device. Verify that this device is associated with a valid identifier.", 3)
        exit()

    
    process_timing("start", "Dashcam/Calculations")
    last_alert_minimum_framerate_time = 0 # This value holds the last time a minimum frame-rate alert was displayed. Here the value is initialized.

    if (float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["min"]) == 0): # Check to see if the minimum frame-rate is 0.
        expected_time_since_last_frame_slowest = 100
    else:
        expected_time_since_last_frame_slowest = 1/float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["min"]) # Calculate the longest expected time between two frames.
    expected_time_since_last_frame_fastest = 1/float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"]) # Calculate the shortest expected time between two frames.
    process_timing("end", "Dashcam/Calculations")

    save_this_segment = False # This will be set to True when the saving trigger is created. The current and previous dashcam segments are saved immediately when the trigger is created, but this allows the completed segment to be saved once the next segment is started, such that the saved segment doesn't cut off at the moment the user triggered a save.
    last_frame_captured = time.time() # This will hold the exact time that the last frame was captured. Here, the value is initialized to the current time before any frames have been captured.
    while dashcam_recording_active: # Only run while the dashcam recording flag is set to 'True'. While this flag changes to 'False' this recording process should exit entirely.
        heartbeat() # Issue a status heartbeat.

        process_timing("start", "Dashcam/Calculations")
        time_since_last_frame = time.time()-last_frame_captured # Calculate the time (in seconds) since the last frame was captured.
        instant_framerate[device] = 1/time_since_last_frame
        if (time_since_last_frame > expected_time_since_last_frame_slowest): # Check see if the current frame-rate is below the minimum expected frame-rate.
            if (frames_since_last_segment > 1 and previously_parked == False): # Check to make sure we aren't at the very beginning of recording, where frame-rate might be inconsistent.
                if (time.time() - last_alert_minimum_framerate_time > 1): # Check to see if at least 1 second has passed since the last minimum frame-rate alert.
                    display_message("The framerate on '" + device + "' (" + str(round((1/time_since_last_frame)*100)/100) + "fps) has fallen below the minimum frame-rate.", 2)
            last_alert_minimum_framerate_time = time.time() # Record the current time as the time that the last minimum frame-rate alert was shown.
        elif (time_since_last_frame < expected_time_since_last_frame_fastest): # Check see if the current frame-rate is above the maximum expected frame-rate.
            time.sleep(expected_time_since_last_frame_fastest - time_since_last_frame) # Wait to force the frame-rate to stay below the maximum limit.
        process_timing("end", "Dashcam/Calculations")

        last_frame_captured = time.time() # Update the time that the last frame was captured immediately before capturing the next frame.
        process_timing("start", "Dashcam/Video Capture")
        ret, frame = capture.read() # Capture a frame.
        process_timing("end", "Dashcam/Video Capture")
        if not ret: # Check to see if the frame failed to be read.
            display_message("Failed to receive video frame from the '" + device  + "' device. It is possible this device has been disconnected.", 3)
            exit()
        frames_captured+=1
        if (config["dashcam"]["capture"]["video"]["devices"][device]["flip"]): # Check to see if Predator is convered to flip this capture device's output.
            process_timing("start", "Dashcam/Image Manipulation")
            frame = cv2.rotate(frame, cv2.ROTATE_180) # Flip the frame by 180 degrees.
            process_timing("end", "Dashcam/Image Manipulation")
        if (config["dashcam"]["parked"]["recording"]["buffer"] > 0): # Check to see if the frame buffer is greater than 0 before adding frames to the buffer.
            process_timing("start", "Dashcam/Frame Buffer")
            frame_history.append(apply_dashcam_stamps(frame)) # Add the frame that was just captured to the frame buffer.
            if (len(frame_history) > config["dashcam"]["parked"]["recording"]["buffer"]): # Check to see if the frame buffer has exceeded the maximum length.
                frame_history = frame_history[-config["dashcam"]["parked"]["recording"]["buffer"]:] # Trim the frame buffer to the appropriate length.
            process_timing("end", "Dashcam/Frame Buffer")


        process_timing("start", "Dashcam/Interface Interactions")
        if (os.path.exists(config["general"]["interface_directory"] + "/" + config["dashcam"]["saving"]["trigger"])): # Check to see if the trigger file exists.
            if (config["dashcam"]["capture"]["audio"]["merge"] == True and config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if Predator is configured to merge audio and video files.
                dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[video_filepath], name="DashcamSegmentSave") # Create the thread to save this dashcam segment.
                dashcam_segment_saving.start() # Start the dashcam segment saving thread.
                if (config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if audio recording is enabled.
                    dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[audio_filepath], name="DashcamSegmentSave") # Create the thread to save the current audio segment as a separate file, even though merging is enabled, since the merge won't have been executed yet.
                    dashcam_segment_saving.start() # Start the dashcam segment saving thread.
                if (last_filename != ""): # Check to see if a last filename is set before attempting to copy the last merged video file.
                    dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[str(last_filename + ".mkv")], name="DashcamSegmentSave") # Create the thread to save the last video segment.
                    dashcam_segment_saving.start() # Start the dashcam segment saving thread.
            else: # Otherwise, save the last segment as separate audio/video files.
                dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[video_filepath, last_video_filepath], name="DashcamSegmentSave") # Create the thread to save the current and last video segments.
                dashcam_segment_saving.start() # Start the dashcam segment saving thread.
                if (config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if audio recording is enabled.
                    dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[audio_filepath, last_audio_filepath], name="DashcamSegmentSave") # Create the thread to save the current and last audio segments.
                    dashcam_segment_saving.start() # Start the dashcam segment saving thread.
            save_this_segment = True # This flag causes Predator to save this entire segment again when the next segment is started.
        process_timing("end", "Dashcam/Interface Interactions")


        if (parked == True): # Check to see if the vehicle is parked.
            update_state("dashcam/parked_dormant")
            if (previously_parked == False): # Check to see if this is the first loop in parking mode since the last time normal recording took place.
                output = None # Release the video output file.
                process_timing("start", "Dashcam/File Merging")
                if (config["dashcam"]["capture"]["audio"]["merge"] == True and config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if Predator is configured to merge audio and video files.
                    last_filename_merged = file_name + ".mkv"
                    if (os.path.exists(audio_filepath) and os.path.exists(video_filepath)): # Check to make sure there is actually an audio and video file to merge.
                        audio_video_merge = threading.Thread(target=merge_audio_video, args=[video_filepath, audio_filepath, last_filename_merged], name="AudioVideoMerge") # Create the thread to merge the audio and video files.
                        audio_video_merge.start() # Start the merging thread.
                process_timing("end", "Dashcam/File Merging")

            previously_parked = True # Indicate that Predator was parked so that we know that the next loop isn't the first loop of Predator being in parked mode.

            process_timing("start", "Dashcam/Audio Processing")
            if (config["dashcam"]["capture"]["audio"]["enabled"] == True):
                if (audio_recorder.poll() is None): # Check to see if there is an active audio recorder.
                    audio_recorder.terminate() # Kill the active audio recorder.
            contours, moving_percentage = detect_motion(frame, background_subtractor) # Run motion analysis on this frame.
            process_timing("end", "Dashcam/Audio Processing")


            if (moving_percentage > float(config["dashcam"]["parked"]["recording"]["sensitivity"])): # Check to see if there is movement that exceeds the sensitivity threshold.
                display_message("Detected motion.", 1)
                if (config["dashcam"]["notifications"]["reticulum"]["enabled"] == True and config["dashcam"]["notifications"]["reticulum"]["events"]["motion_detected"]["enabled"] == True): # Check to see if Predator is configured to send motion detection notifications over Reticulum.
                    for destination in config["dashcam"]["notifications"]["reticulum"]["destinations"]: # Iterate over each configured destination.
                        reticulum.lxmf_send_message(str(config["dashcam"]["notifications"]["reticulum"]["instance_name"]) + " has detected motion while parked", destination) # Send a Reticulum LXMF message to this destination.
                framerate = record_parked_motion(capture, framerate, width, height, device, directory, frame_history) # Run parked motion recording, and update the framerate to the newly calculated framerate.
                process_timing("start", "Dashcam/Motion Detection")
                background_subtractor = cv2.createBackgroundSubtractorMOG2() # Reset the background subtractor after motion is detected.
                process_timing("end", "Dashcam/Motion Detection")


        else: # If the vehicle is not parked, then run normal video processing.
            update_state("dashcam/normal", instant_framerate)
            previously_parked = False
            if (utils.get_time() > first_segment_started_time + (segment_number+1)*config["dashcam"]["saving"]["segment_length"]): # Check to see if it is time to start a new segment.
                process_timing("start", "Dashcam/Calculations")
                # Handle the start of a new segment.
                segment_number+=1 # Increment the segment counter.
                last_video_filepath = video_filepath # Record the file name of the current video segment before updating it.
                last_audio_filepath = audio_filepath # Record the file name of the current audio segment before updating it.
                last_filename = file_name # Record the base file name of the current segment before updating.

                calculated_framerate = frames_since_last_segment / (utils.get_time() - segment_start_time) # Calculate the frame-rate of the last segment.
                process_timing("end", "Dashcam/Calculations")
                segment_start_time = utils.get_time() # Update the segment start time.
                file_name = directory + "/predator_dashcam_" + str(round(first_segment_started_time + (segment_number*config["dashcam"]["saving"]["segment_length"]))) + "_" + str(device) + "_" + str(segment_number) + "_N"

                video_filepath = file_name + ".avi" # Update the file path.

                process_timing("start", "Dashcam/Audio Processing")
                if (config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if audio recording is enabled in the configuration.
                    audio_recorder.terminate() # Kill the previous segment's audio recorder.
                    audio_filepath = file_name + "." + str(config["dashcam"]["capture"]["audio"]["extension"])
                    audio_recorder = subprocess.Popen(["arecord", "-q", "--format=cd", audio_filepath], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) # Start the next segment's audio recorder.
                process_timing("end", "Dashcam/Audio Processing")

                output = None # Release the previous video output file.

                process_timing("start", "Dashcam/Calculations")
                if (calculated_framerate > float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"])): # Check to see if the calculated frame-rate exceeds the maximum allowed frame-rate.
                    calculated_framerate = float(config["dashcam"]["capture"]["video"]["devices"][device]["framerate"]["max"]) # Set the frame-rate to the maximum allowed frame-rate.
                process_timing("end", "Dashcam/Calculations")
                process_timing("start", "Dashcam/Writing")
                output = cv2.VideoWriter(video_filepath, cv2.VideoWriter_fourcc(*'XVID'), float(calculated_framerate), (width,  height)) # Update the video output.
                process_timing("end", "Dashcam/Writing")
                frames_since_last_segment = 0 # This will count the number of frames in this video segment.

                process_timing("start", "Dashcam/File Merging")
                if (config["dashcam"]["capture"]["audio"]["merge"] == True and config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if Predator is configured to merge audio and video files.
                    last_filename_merged = last_filename + ".mkv"
                    if (os.path.exists(last_audio_filepath) == False):
                        display_message("The audio file was missing during audio/video merging. It is possible something has gone wrong with recording.", 2)
                    else:
                        merge_audio_video(last_video_filepath, last_audio_filepath, last_filename_merged) # Run the audio/video merge.
                process_timing("end", "Dashcam/File Merging")
                
                if (save_this_segment == True): # Now that the new segment has been started, check to see if the segment that was just completed should be saved.
                    if (config["dashcam"]["capture"]["audio"]["merge"] == True and config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if Predator is configured to merge audio and video files.
                        if (os.path.exists(last_filename_merged)): # Check to make sure the merged video file actually exists before saving.
                            save_dashcam_segments(last_filename_merged) # Save the merged video/audio file. At this point "last_filename" is actually the segment that was just completed, since we just started a new segment.

                            # Now that the merged file has been saved, go back and delete the separate files that were saved previously.
                            base_file = config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "/" + os.path.splitext(os.path.basename(last_filename_merged))[0]
                            os.system("rm '" + base_file + ".avi'")
                            os.system("rm '" + base_file + "." + str(config["dashcam"]["capture"]["audio"]["extension"]) + "'")
                        else: # If the merged video file doesn't exist, it is likely something went wrong with the merging process.
                            display_message("The merged video/audio file did exist when Predator tried to save it. It is likely the merge process has failed unexpectedly. The separate files are being saved as a fallback.", 3)
                            dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[last_video_filepath, last_audio_filepath], name="DashcamSegmentSave") # Create the thread to save the dashcam segment. At this point, "last_video_filepath" is actually the completed previous video segment, since we just started a new segment.
                            dashcam_segment_saving.start() # Start the dashcam segment saving thread.
                    else: # If audio/video merging is disabled, then save the separate video and audio files.
                        dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[last_video_filepath], name="DashcamSegmentSave") # Create the thread to save the dashcam segment. At this point, "last_video_filepath" is actually the completed previous video segment, since we just started a new segment.
                        dashcam_segment_saving.start() # Start the dashcam segment saving thread.
                        if (config["dashcam"]["capture"]["audio"]["enabled"] == True): # Check to see if audio recording is enabled.
                            dashcam_segment_saving = threading.Thread(target=save_dashcam_segments, args=[last_audio_filepath], name="DashcamSegmentSave") # Create the thread to save the dashcam segment. At this point, "last_audio_filepath" is actually the completed previous video segment, since we just started a new segment.
                            dashcam_segment_saving.start() # Start the dashcam segment saving thread.
                    save_this_segment = False # Reset the segment saving flag.


                delete_old_segments() # Handle the erasing of any old dash-cam segments that need to be deleted.


            frames_since_last_segment += 1 # Increment the frame counter.


            frame = apply_dashcam_stamps(frame)

            process_timing("start", "Dashcam/Writing")
            frame_write_thread = threading.Thread(target=write_frame, args=[frame, output], name="FrameWrite")
            frame_write_thread.start()
            process_timing("end", "Dashcam/Writing")

            if (config["developer"]["print_timings"] == True):
                utils.clear(True)
                print(json.dumps(process_timing("dump", ""), indent=4))


    capture.release()
    cv2.destroyAllWindows()



parked = False # Start with parked mode disabled.
def start_dashcam_recording(dashcam_devices, video_width, video_height, directory, background=False): # This function starts dashcam recording on a given list of dashcam devices.
    dashcam_process = [] # Create a placeholder list to store the dashcam processes.
    iteration_counter = 0 # Set the iteration counter to 0 so that we can increment it for each recording device specified.
    global parked
    global dashcam_recording_active
    dashcam_recording_active = True
    
    for device in dashcam_devices: # Run through each camera device specified in the configuration, and launch an OpenCV recording instance for it.
        dashcam_process.append(threading.Thread(target=capture_dashcam_video, args=[directory, device, video_width, video_height], name="Dashcam" + str(dashcam_devices[device]["index"])))
        dashcam_process[iteration_counter].start()

        iteration_counter += 1 # Iterate the counter. This value will be used to create unique file names for each recorded video.
        print("Started dashcam recording on " + str(dashcam_devices[device]["index"])) # Inform the user that recording was initiation for this camera device.

    if (background == False): # If background recording is disabled, then prompt the user to press enter to halt recording.
        try:
            print("Press Ctrl+C to stop dashcam recording...") # Wait for the user to press enter before continuing, since continuing will terminate recording.
            if (config["dashcam"]["parked"]["enabled"] == True): # Check to see if parked mode functionality is enabled.
                last_moved_time = utils.get_time() # This value holds the Unix timestamp of the last time the vehicle exceeded the parking speed threshold.
                while True: # The user can break this loop with Ctrl+C to terminate dashcam recording.
                    if (config["general"]["gps"]["enabled"] == True): # Check to see if GPS is enabled.
                        current_location = get_gps_location() # Get the current GPS location.
                    else:
                        current_location = [0, 0, 0, 0, 0, 0]
                    if (current_location[2] > config["dashcam"]["parked"]["conditions"]["speed"]): # Check to see if the current speed exceeds the parked speed threshold.
                        last_moved_time = utils.get_time()
                    if (utils.get_time() - last_moved_time > config["dashcam"]["parked"]["conditions"]["time"]): # Check to see if the amount of time the vehicle has been stopped exceeds the time threshold to enable parked mode.
                        if (parked == False): # Check to see if Predator wasn't already in parked mode.
                            display_message("Entered parked mode.", 1)
                            if (config["dashcam"]["notifications"]["reticulum"]["enabled"] == True and config["dashcam"]["notifications"]["reticulum"]["events"]["parking_mode_enabled"]["enabled"] == True): # Check to see if Predator is configured to parking mode activation notifications over Reticulum.
                                for destination in config["dashcam"]["notifications"]["reticulum"]["destinations"]: # Iterate over each configured destination.
                                    reticulum.lxmf_send_message(str(config["dashcam"]["notifications"]["reticulum"]["instance_name"]) + " has entered parked mode.", destination) # Send a Reticulum LXMF message to this destination.
                        parked = True # Enter parked mode.
                    else:
                        if (parked == True): # Check to see if Predator wasn't already out of parked mode.
                            display_message("Exited parked mode.", 1)
                            if (config["dashcam"]["notifications"]["reticulum"]["enabled"] == True and config["dashcam"]["notifications"]["reticulum"]["events"]["parking_mode_disabled"]["enabled"] == True): # Check to see if Predator is configured to parking mode deactivation notifications over Reticulum.
                                for destination in config["dashcam"]["notifications"]["reticulum"]["destinations"]: # Iterate over each configured destination.
                                    reticulum.lxmf_send_message(str(config["dashcam"]["notifications"]["reticulum"]["instance_name"]) + " has exited parked mode.", destination) # Send a Reticulum LXMF message to this destination.
                        parked = False # Exit parked mode.
                    
                    time.sleep(1)
        except Exception as exception:
            dashcam_recording_active = False # All dashcam threads are watching this variable globally, and will terminate when it is changed to 'False'.
            display_message("Dashcam recording halted.", 1)
            print(exception)



currently_writing_frame = False
def write_frame(frame, output):
    global currently_writing_frame
    while (currently_writing_frame == True):
        time.sleep(0.001)
    currently_writing_frame = True
    output.write(frame)
    currently_writing_frame = False
