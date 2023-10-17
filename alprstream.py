import csv
import os
import time
import json # Required to process JSON data


predator_root_directory = str(os.path.dirname(os.path.realpath(__file__))) # This variable determines the folder path of the root Predator directory. This should usually automatically recognize itself, but if it doesn't, you can change it manually.


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
style = utils.style # Load style information from the utils script.
debug_message  = utils.debug_message # Load the debug message function from the utils script.
clear = utils.clear # Load the screen clearing function from the utils script.
prompt = utils.prompt # Load the user input prompt function from the utils script.
save_to_file = utils.save_to_file # Load the user input prompt function from the utils script.

import subprocess
import threading


alpr_stream_file_location = "/dev/shm/predator_alpr_stream" # This determines where the text file for streaming ALPR information will be stored.


global queued_plate_reads
queued_plate_reads = []


def alpr_stream():
    if (config["general"]["alpr"]["engine"] == "phantom"): # Check to see if the configure ALPR engine is Phantom.
        alpr_command = "alpr -n " + str(config["general"]["alpr"]["validation"]["guesses"]) + " " + config["realtime"]["image"]["camera"]["device"] + " >> " + alpr_stream_file_location # Set up the Phantom ALPR command.
    if (config["general"]["alpr"]["engine"] == "openalpr"): # Check to see if the configure ALPR engine is OpenALPR.
        alpr_command = "alpr -j -n " + str(config["general"]["alpr"]["validation"]["guesses"]) + " " + config["realtime"]["image"]["camera"]["device"] + " >> " + alpr_stream_file_location # Set up the Phantom ALPR command.
    alpr_stream_process = os.popen(alpr_command) # Execute the ALPR command.

def alpr_stream_maintainer(): # This function runs an endless loop that maintains
    global queued_plate_reads
    while True:
        time.sleep(0.3) # Delay for a short period of time before each loop so that the ALPR stream has time to output some results.
        stream_file = open(alpr_stream_file_location) # Open the ALPR stream file.
        stream_file_contents = stream_file.readlines() # Read the stream file line by line.
        stream_file.close() # Close the ALPR stream file.
        save_to_file(alpr_stream_file_location, "", True) # Erase the contents of the ALPR stream file.

        for message in stream_file_contents: # Iterate through each line in the loaded stream file contents.
            message = json.loads(message) # Parse each line into JSON.
            for plate in message["results"]: # Iterate through each license plate in this line.
                queued_plate_reads.append(plate) # Add each license plate to the license plate queue.

def start_alpr_stream(): # This function starts the ALPR stream threads.
    debug_message("Opening ALPR message stream")
    alpr_stream_thread = threading.Thread(target=alpr_stream, name="ALPRStream") # Initialize the ALPR stream thread.
    alpr_stream_thread.start() # Start the ALPR stream thread.
    alpr_stream_maintainer_thread = threading.Thread(target=alpr_stream_maintainer, name="ALPRStreamMaintainer") # Initialize the ALPR stream maintainer thread.
    alpr_stream_maintainer_thread.start() # Start the ALPR stream maintainer thread.


def alpr_get_queued_plates(): # This function is used to fetch the latest queue of detected license plates.
    global queued_plate_reads
    results_to_return = queued_plate_reads
    queued_plate_reads = [] # Clear the license plate queue.
    return results_to_return
