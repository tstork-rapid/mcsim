#! /usr/bin/env python3
import re
from os.path import exists
from sys import exit
from glob import glob
import numpy as np
import NumpyIm as npi
from runcmd import runcmd
import subprocess


# Define the pattern to match filenames starting with "sim" and ending with 'w' followed by two digits and with '.avg.im'
pattern_re = re.compile(r"sim.*w(\d{2})\.avg\.im")
pattern_txt = "sim*w??.avg.im"
match_group = 1

# Check if the first output file exists and exit if so
if exists("combined.avg.w01.im"):
    print("Output files already exist. Exiting to prevent overwritting")
    exit(1)

# Detect if only 1 seed exists by counting the .avg files
if len(glob(pattern_txt)) < 1:
    # Change patterns to not search for averaged images but for raw seed outputs
    pattern_re = re.compile(r"sim.*_(\d*)\.w(\d{2})\.im")
    pattern_txt = pattern_txt = "sim*w??.im"
    match_group = 2

    # Initialize a list to store the extracted numbers
    numbers = []

    # Iterate over files in the current directory
    for filename in glob(pattern_txt):
        match = pattern_re.search(filename)
        if match:
            number = int(match.group(1))
            numbers.append(number)
    
    # Find min and max number if any were found
    min_number = min(numbers) if numbers else None
    max_number = max(numbers) if numbers else None
    
    if min_number != max_number:
        print("More than one seed found but no averaged images found. Ensure avg_done_sims.py was ran.")
        exit(1)
    else:
        print("No averaged images found. Continuing with single seed")

# Initialize a list to store the extracted numbers
numbers = []

# Iterate over files in the current directory
for filename in glob(pattern_txt):
    match = pattern_re.search(filename)
    if match:
        number = int(match.group(match_group))
        numbers.append(number)

# Find max number if any were found
max_number = max(numbers) if numbers else None

# Create range of numbers to index
num_range = list(range(1, max_number + 1))

for i in num_range:
    # Create window number as text
    if i < 10:
        num_txt = "0" + str(i)
    else:
        num_txt = str(i)

    # Create pattern to search for
    pattern_num = pattern_txt.replace("??", num_txt)

    # Initialize files
    files = []

    # Make a list of all file names with current window number
    # This grabs all inserts, all radionuclides of that window number
    for file in glob(pattern_num):
        files.append(file)
    
    # Initialize loop variables
    num_summed = 0
    outf = "combined.avg.w" + num_txt + ".im"

    for file in files:
        try:
            pix = npi.ArrayFromIm(file)
        except npi.error as e:
            print(f"error reading {file}")
            print(f"   skipping")
            continue
        if num_summed == 0:
            sum = pix.astype(np.float64)
        else:
            sum += pix.astype(np.float64)
        num_summed += 1
    if num_summed <= 1:
        print(" summed 1 or fewer images for {outf}: no output generated")
    else:
        print(f"saving {outf}. summed {num_summed}")
        try:
            npi.ArrayToIm(sum.astype(np.float32), outf)

            # Find original simulation outputs
            sims = "sim_*w" + num_txt +".im"
            sim_files = []
            for sim in glob(sims):
                sim_files.append(sim)
            
            # Copy header from a simulation output from the current window to the summed output
            cmd = f"imgcpinfo {sim_files[0]} {outf}" # overwrites previous output
            print("Running: " + cmd)
            runcmd(cmd,1)
            
            # Determine scale factor to get images to 128x128
            shape = sum.shape
            x_factor = shape[2]/128
            y_factor = shape[1]/128

            # Collapse the images to 128x128 if needed
            if x_factor > 1 or y_factor > 1:
                cmd = f"collapse {x_factor} {y_factor} {outf} collapsed.{outf}"
                print("Running: " + cmd)
                runcmd(cmd,1)

                # Copy header from pre-collapsed images to collapsed images
                cmd = f"imgcpinfo {outf} collapsed.{outf}" # overwrites previous output
                print("Running: " + cmd)
                runcmd(cmd,1)

                # Get new pixel spacing rows and columns
                pix_size = subprocess.check_output(["imghdr", "-i", "Pixel Size", outf])
                pix_size = pix_size.decode('ascii').strip().split()
                row_size = float(pix_size[0]) * x_factor
                col_size = float(pix_size[1]) * y_factor

                # Update pixel spacing rows and columns
                cmd = f"imsetinfo -i \"Pixel Spacing Rows\" \"{row_size}\" -i \"Pixel Spacing Cols\" \"{col_size}\" collapsed.{outf}"
                print("Running: " + cmd)
                runcmd(cmd,1)

        except npi.error as e:
            print("error generating {outf}: {e}")
            exit(1)

exit(0)
