#! /usr/bin/env python3
import re
from os.path import exists
from sys import exit
from glob import glob
from runcmd import runcmd


def combine_images(files, num_txt, prefix=""):
    """
    Combines file 1 with file 2, file 3 with file 4, and so on. If there is an odd number of files, it will return the last file with the combined list.

    Inputs:
        files: list of file names as strings
        num_txt: simind window number as text (including any leading zeros)
        prefix: additional text to put in the outfile name
    Outputs:
        outfiles: list of file names as strings
        saves combined images as temp files
    """
    # Initialize outfiles
    outfiles = []

    for i in range(0, len(files) - 1, 2):
        # Initialize command for combining .im files
        infile1 = files[i]
        infile2 = files[i + 1]
        outfile = prefix + "temp.w" + num_txt + "." + str(i) + ".im"
        cmd = f"add -A 1 -B 1 {infile1} {infile2} {outfile}"

        # Run command
        runcmd(cmd, 1)
        print("Running: " + cmd)

        # Track outfiles
        outfiles.append(outfile)

    # If there is an odd number of files, append the file that didn't get combined to the output list
    if len(files) % 2 == 1:
        outfiles.append(files[-1])

    return outfiles


# Define the pattern to match filenames starting with "sim" and ending with 'w' followed by two digits and with '.avg.im'
pattern_re = re.compile(r"sim.*w(\d{2})\.avg\.im")
pattern_txt = "sim*w??.avg.im"
match_group = 1

# Check if the first output file exists and exit if so
if exists("combined.w01.avg.im"):
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
    for file in glob(pattern_num):
        files.append(file)

    # Initialize while loop variables
    prefix = "run"
    j = 0
    outfiles = files
    if len(files) > 2:
        continue_combining = True
    else:
        continue_combining = False

    # Combine all images until there are only 2 left
    while continue_combining:
        # Print status
        print("Combining " + str(len(outfiles)) + " files:")
        print(outfiles)

        # Increment counter
        j = j + 1

        # Combine images
        outfiles = combine_images(outfiles, num_txt, "run" + str(j) + ".")

        # Break out of the look when there are 2 files left to combine
        if len(outfiles) == 2:
            continue_combining = False

    # Combine last 2 images with better name
    final_name = "combined.w" + num_txt + ".avg.im"
    cmd = f"add -A 1 -B 1 {outfiles[0]} {outfiles[1]} {final_name}"
    runcmd(cmd, 1)
    print("Running: " + cmd)

# Remove all temp files
cmd = "rm *temp*.im"
runcmd(cmd, 1)
print("Running: " + cmd)

exit(0)
