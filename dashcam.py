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
get_gps_location = utils.get_gps_location
heartbeat = utils.heartbeat
convert_speed = utils.convert_speed

import threading
import time
import cv2
import subprocess # Required for starting some shell commands
import sys
import datetime # Required for converting between timestamps and human readable date/time information
if (config["realtime"]["gps"]["enabled"] == True): # Only import the GPS libraries if GPS settings are enabled.
    from gps import * # Required to access GPS information.
    import gpsd





def benchmark_camera_framerate(device, frames=5): # This function benchmarks a given camera to determine its framerate.
    global config

    resolution = [config["dashcam"]["capture"]["resolution"]["width"], config["dashcam"]["capture"]["resolution"]["height"]] # This determines the resolution that will be used for the video capture device.
    capture = cv2.VideoCapture(config["dashcam"]["capture"]["devices"][device]); # Open the video capture device.

    capture.set(cv2.CAP_PROP_FRAME_WIDTH,resolution[0]) # Set the video stream width.
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT,resolution[1]) # Set the video stream height.

    debug_message("Running benchmark for '" + device + "'...")

    for i in range(0, 10): # Loop a few times to allow the camera to warm up before the benchmark starts.
        ret, frame = capture.read() # Capture a video frame.
    start_time = time.time() # Record the exact time that the benchmark started.
    for i in range(0, frames): # Run until the specified number of frames have been captured.
        ret, frame = capture.read() # Capture a video frame.
        stamp_test = str(round(time.time()*100)/100) + " PLACEHOLDER" + str(round(time.time()/2)) # Manipulate a few random values to simulate the generation of the overlay stamp.
        cv2.putText(frame, stamp_test, (10, 10), 2, 0.8, (255,255,255)) # Add the test stamp to the video frame.

    end_time = time.time() # Record the exact time that the benchmark ended.
    total_time = end_time - start_time # Calculate how many seconds the benchmark took to complete.
    fps = frames / total_time # Calculate the number of frames captured per second.
    debug_message("Capture device '" + device + "' runs at " + str(round(fps*10)/10) + "fps")
    return fps # Return the calculated FPS.






# This function is called when the lock trigger file is created to save the current and last segments.
def save_dashcam_segments(current_segment, last_segment=""):
    global config

    if (os.path.isdir(config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"]) == False): # Check to see if the saved dashcam video folder needs to be created.
        os.system("mkdir -p '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Create the saved dashcam video directory.
    time.sleep(0.3) # Wait for a short period of time so that other dashcam recording threads have time to detect the trigger file.
    if (os.path.isdir(config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"])): # Check to see if the dashcam saving directory exists.
        os.system("cp '" + current_segment + "' '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Copy the current dashcam video segment to the saved folder.
        if (last_segment != ""): # Check to see if there is a "last file" to copy.
            os.system("cp '" + last_segment + "' '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Copy the last dashcam video segment to the saved folder.
    else:
        display_message("The dashcam saving directory does not exist, and could not be created. The dashcam video could not be locked.", 2)
    display_message("Saved the current dashcam segment.", 1)
    os.system("rm -rf '" + config["general"]["interface_directory"] + "/" + config["dashcam"]["saving"]["trigger"] + "'") # Remove the dashcam lock trigger file.
    if (os.path.exists(config["general"]["interface_directory"] + "/" + config["dashcam"]["saving"]["trigger"])): # Check to see if the trigger file exists even after it should have been removed.
        display_message("Unable to remove trigger file.", 3)




dashcam_recording_active = False
parked = False

def capture_dashcam_video(directory, device="main", width=1280, height=720):
    global dashcam_recording_active
    global parked


    device_id = config["dashcam"]["capture"]["devices"][device]

    if (os.path.isdir(config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"]) == False): # Check to see if the saved dashcam video folder needs to be created.
        os.system("mkdir -p '" + config["general"]["working_directory"] + "/" + config["dashcam"]["saving"]["directory"] + "'") # Create the saved dashcam video directory.

    framerate = benchmark_camera_framerate(device) # Benchmark this capture device to determine its operating framerate.

    capture = cv2.VideoCapture(device_id) # Open the video stream.
    capture.set(cv2.CAP_PROP_FRAME_WIDTH,width) # Set the video stream width.
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT,height) # Set the video stream height.
    total_image_area = width * height # Calculate the total number of pixels in the image.
    background_subtractor = cv2.createBackgroundSubtractorMOG2() # Initialize the background subtractor for motion detect.
    last_motion_detection = 0 # This will hold the timestamp of the last time motion was detected.

    segment_number = 0 # This variable keeps track of the segment number, and will be incremented each time a new segment is started.
    segment_start_time = time.time() # This variable keeps track of when the current segment was started. It will be reset each time a new segment is started.
    frames_since_last_segment = 0 # This will count the number of frames in this video segment.

    file = directory + "/predator_dashcam_" + str(round(time.time())) + "_" + str(device) + "_" + str(segment_number) + "_N.avi" # Determine the initial file path.
    last_file = "" # Initialize the path of the last file to just be a blank string.
    output = cv2.VideoWriter(file, cv2.VideoWriter_fourcc(*'XVID'), float(framerate), (width,  height))

    if (capture is None or not capture.isOpened()):
        display_message("Failed to start dashcam video capture using '" + device  + "' device. Verify that this device is associated with a valid identifier.", 3)
        exit()

    save_this_segment = False # This will be set to True when the saving trigger is created. The current and previous dashcam segments are saved immediately when the trigger is created, but this allows the completed segment to be saved once the next segment is started, such that the saved segment doesn't cut off at the moment the user triggered a save.
    while dashcam_recording_active: # Only run while the dashcam recording flag is set to 'True'.
        heartbeat() # Issue a status heartbeat.
        if (os.path.exists(config["general"]["interface_directory"] + "/" + config["dashcam"]["saving"]["trigger"])): # Check to see if the trigger file exists.
            save_dashcam_segments(file, last_file)
            save_this_segment = True


        if (parked == True): # Check to see if the vehicle is parked before running motion detection.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fgmask = background_subtractor.apply(gray)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fgmask = cv2.erode(fgmask, kernel, iterations=1)
            fgmask = cv2.dilate(fgmask, kernel, iterations=1)
            contours, hierarchy = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            moving_area = 0 # This value will hold the number of pixels in the image that are moving.
            for contour in contours: # Iterate through each contour.
                moving_area += cv2.contourArea(contour) # Increment the moving_area counter by the number of pixels in the contour.

            moving_percentage = moving_area / total_image_area # Calculate the percentage of the frame that is in motion.
            moving_percentage_human = "{:.5f}%".format(moving_percentage*100) # Convert the moving percentage to a human-readable string.
            if (moving_percentage > float(config["dashcam"]["parked"]["recording"]["sensitivity"])): # Check to see if there is movement that exceeds the sensitivity threshold.
                if (moving_percentage < 0.9): # Check to make sure the amount of motion isn't above 90% to prevent camera's exposure adjustments from triggering motion detection.
                    if (time.time() - last_motion_detection > 2): # Check to see if it has been at least 2 seconds since motion was last detected before displaying the motion detection debug message.
                        debug_message("Detected motion")
                    last_motion_detection = time.time() # Update the last time that motion was detected to the current time.
        else: # If the vehicle is not parked, clear some of the motion detection variables.
            contours = []


        if (time.time()-segment_start_time > config["dashcam"]["capture"]["segment_length"]): # Check to see if this segment has exceeded the segment length time.
            # Handle the start of a new segment.
            segment_number+=1 # Increment the segment counter.
            last_file = file # Record the file name of the current segment before updating it.
            if (parked == True):
                file = directory + "/predator_dashcam_" + str(round(time.time())) + "_" + str(device) + "_" + str(segment_number) + "_P.avi" # Update the file path.
            else:
                file = directory + "/predator_dashcam_" + str(round(time.time())) + "_" + str(device) + "_" + str(segment_number) + "_N.avi" # Update the file path.
            if (parked == False or time.time() - last_motion_detection < 10): # Check to see if recording is active before intitializing the video file.
                calculated_framerate = frames_since_last_segment / (time.time() - segment_start_time) # Calculate the frame-rate of the last segment.
                output = cv2.VideoWriter(file, cv2.VideoWriter_fourcc(*'XVID'), float(calculated_framerate), (width,  height)) # Update the video output.
            segment_start_time = time.time() # Update the segment start time.
            frames_since_last_segment = 0 # This will count the number of frames in this video segment.

            
            if (save_this_segment == True): # Now that the new segment has been started, check to see if the completed segment should be saved.
                save_dashcam_segments(last_file) # In this case, "last_file" is actually the completed previous segment, since we just started a new segment.
                save_this_segment = False # Reset the segment saving flag.

            # Handle the deletion of any expired dashcam videos.
            dashcam_files_list_command = "ls " + config["general"]["working_directory"] + " | grep predator_dashcam" # Set up the command to get a list of all unsaved dashcam videos in the working directory.
            dashcam_files = str(os.popen(dashcam_files_list_command).read())[:-1].splitlines() # Run the command, and record the raw output string.
            dashcam_files = sorted(dashcam_files) # Sort the dashcam files alphabetically to get them in chronological order.
            if (len(dashcam_files) > int(config["dashcam"]["saving"]["unsaved_history_length"])): # Check to see if the current number of dashcam segments in the working directory is higher than the configured history length.
                videos_to_delete = dashcam_files[0:len(dashcam_files) - int(config["dashcam"]["saving"]["unsaved_history_length"])] # Create a list of all of the videos that need to be deleted.
                for video in videos_to_delete: # Iterate through each video that needs to be deleted.
                    os.system("timeout 5 rm '" + config["general"]["working_directory"] + "/" + video + "'") # Delete the dashcam segment.


        ret, frame = capture.read() # Capture a frame.
        frames_since_last_segment += 1 # Increment the frame counter.
        if not ret: # Check to see if the frame failed to be read.
            print("Can't receive frame")
            display_message("Failed to receive video frame from '" + device  + "' device. It is possible this device was disconnected.", 3)
            break


        if (parked == False or time.time() - last_motion_detection < 10): # Check to see if recording is active so we don't do unnecessary image processing.
            if (config["dashcam"]["parked"]["recording"]["highlight_motion"]["enabled"] == True):
                for contour in contours: # Iterate through each contour.
                    if cv2.contourArea(contour) > 10: # Check to see if this contour is big enough to be worth highlighting.
                        color = config["dashcam"]["parked"]["recording"]["highlight_motion"]["color"]
                        x, y, w, h = cv2.boundingRect(contour) # Define the edges of the contour.
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (color[2], color[1], color[0]), 2) # Draw a box around the contour in the frame.
                        del color
            main_stamp_position = [10, height - 10] # Determine where the main overlay stamp should be positioned in the video stream.
            main_stamp = ""
            if (config["dashcam"]["stamps"]["main"]["unix_time"]["enabled"] == True): # Check to see if the Unix epoch time stamp is enabled.
                main_stamp = main_stamp + str(round(time.time())) + " " # Add the current Unix epoch time to the main stamp.
            if (config["dashcam"]["stamps"]["main"]["date"]["enabled"] == True): # Check to see if the date stamp is enabled.
                main_stamp = main_stamp + str(datetime.datetime.today().strftime("%Y-%m-%d")) + " "  # Add the date to the main stamp.
            if (config["dashcam"]["stamps"]["main"]["time"]["enabled"] == True): # Check to see if the time stamp is enabled.
                main_stamp = main_stamp + str(datetime.datetime.now().strftime("%H:%M:%S")) + " "  # Add the time to the main stamp.
            main_stamp = main_stamp  + "  " + config["dashcam"]["stamps"]["main"]["message_1"] + "  " + config["dashcam"]["stamps"]["main"]["message_2"] # Add the customizable messages to the overlay stamp.

            gps_stamp_position = [10, 30] # Determine where the GPS overlay stamp should be positioned in the video stream.
            gps_stamp = "" # Set the GPS to a blank placeholder. Elements will be added to this in the next steps.
            current_location = get_gps_location() # Get the current location.
            if (config["dashcam"]["stamps"]["gps"]["location"]["enabled"] == True): # Check to see if the GPS location stamp is enabled.
                gps_stamp = gps_stamp + "(" + str(round(current_location[0]*100000)/100000) + ", " + str(round(current_location[1]*100000)/100000) + ")  " # Add the current coordinates to the GPS stamp.
            if (config["dashcam"]["stamps"]["gps"]["altitude"]["enabled"] == True): # Check to see if the GPS altitude stamp is enabled.
                gps_stamp = gps_stamp + str(round(current_location[3])) + "m  " # Add the current altitude to the GPS stamp.
            if (config["dashcam"]["stamps"]["gps"]["speed"]["enabled"] == True): # Check to see if the GPS speed stamp is enabled.
                gps_stamp = gps_stamp + str(round(convert_speed(current_location[2],config["dashcam"]["stamps"]["gps"]["speed"]["unit"])*10)/10) + config["dashcam"]["stamps"]["gps"]["speed"]["unit"] + "  " # Add the current speed to the GPS stamp.

            # Determine the font color of the stamps from the configuration.
            main_stamp_color = config["dashcam"]["stamps"]["main"]["color"]
            gps_stamp_color = config["dashcam"]["stamps"]["gps"]["color"]

            # Add the stamps to the video stream.
            cv2.putText(frame, main_stamp, (main_stamp_position[0], main_stamp_position[1]), 2, 0.8, (main_stamp_color[2], main_stamp_color[1], main_stamp_color[0])) # Add the main overlay stamp to the video stream.
            cv2.putText(frame, gps_stamp, (gps_stamp_position[0], gps_stamp_position[1]), 2, 0.8, (gps_stamp_color[2], gps_stamp_color[1], gps_stamp_color[0])) # Add the GPS overlay stamp to the video stream.

            output.write(frame) # Save this frame to the video.

    capture.release()
    cv2.destroyAllWindows()



def start_dashcam_recording(dashcam_devices, video_width, video_height, directory, background=False): # This function starts dashcam recording on a given list of dashcam devices.
    dashcam_process = [] # Create a placeholder list to store the dashcam processes.
    iteration_counter = 0 # Set the iteration counter to 0 so that we can increment it for each recording device specified.
    global parked
    global dashcam_recording_active
    dashcam_recording_active = True
    
    for device in dashcam_devices: # Run through each camera device specified in the configuration, and launch an FFMPEG recording instance for it.
        dashcam_process.append(threading.Thread(target=capture_dashcam_video, args=[directory, device, video_width, video_height], name="Dashcam" + str(iteration_counter)))
        dashcam_process[iteration_counter].start()

        iteration_counter += 1 # Iterate the counter. This value will be used to create unique file names for each recorded video.
        print("Started dashcam recording on " + str(dashcam_devices[device])) # Inform the user that recording was initiation for this camera device.

    if (background == False): # If background recording is disabled, then prompt the user to press enter to halt recording.
        try:
            print("Press Ctrl+C to stop dashcam recording...") # Wait for the user to press enter before continuing, since continuing will terminate recording.
            if (config["dashcam"]["parked"]["enabled"] == True): # Check to see if parked mode functionality is enabled.
                last_moved_time = time.time() # This value holds the Unix timestamp of the last time the vehicle exceeded the parking speed threshold.
                while True: # The user can break this loop with Ctrl+C to terminate dashcam recording.
                    current_location = get_gps_location() # Get the current GPS location.
                    if (current_location[2] > config["dashcam"]["parked"]["conditions"]["speed"]): # Check to see if the current speed exceeds the parked speed threshold.
                        last_moved_time = time.time()
                    if (time.time() - last_moved_time > config["dashcam"]["parked"]["conditions"]["time"]): # Check to see if the amount of time the vehicle has been stopped exceeds the time threshold to enable parked mode.
                        if (parked == False): # Check to see if Predator wasn't already in parked mode.
                            debug_message("Entered parked mode") # Display a debug message, since parked mode was entered just now.
                        parked = True # Enter parked mode.
                    else:
                        if (parked == True): # Check to see if Predator wasn't already out of parked mode.
                            debug_message("Exited parked mode") # Display a debug message, since parked mode was exited just now.
                        parked = False # Exit parked mode.
                    
                    time.sleep(1)
        except:
            dashcam_recording_active = False # All dashcam threads are watching this variable globally, and will terminate when it is changed to 'False'.
            print("Dashcam recording halted.")
