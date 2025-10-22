#! /usr/bin/env python3
import re
from os.path import exists
from sys import exit, argv
from glob import glob
import numpy as np
import NumpyIm as npi
from runcmd import runcmd, waitall
import subprocess

def reduce_proj_to_128(file):
    '''
    Downsample projection images to 128x128 while retaining header information.
    Inputs:
        file: file name of the data as .im
    Outputs:
        if downsampling is needed: collapsed.{file}
        if no downsampling is needed: none
    '''
    
    # Determine scale factor to get images to 128x128
    pix = npi.ArrayFromIm(file)
    shape = pix.shape
    x_factor = shape[2]/128
    y_factor = shape[1]/128

    # Collapse the images to 128x128 if needed
    if x_factor > 1 or y_factor > 1:
        outf = f"collapsed.{file}"
        cmd = f"collapse {x_factor} {y_factor} {file} {outf}"
        print("Running: " + cmd)
        runcmd(cmd,1,2)

        # Copy header from pre-collapsed images to collapsed images
        copy_header(file, outf)

        # Get new pixel spacing rows and columns
        pix_size = subprocess.check_output(["imghdr", "-i", "Pixel Size", file])
        pix_size = pix_size.decode('ascii').strip().split()
        row_size = float(pix_size[0]) * x_factor
        col_size = float(pix_size[1]) * y_factor

        # Update pixel spacing rows and columns
        cmd = f"imsetinfo -i \"Pixel Spacing Rows\" \"{row_size}\" -i \"Pixel Spacing Cols\" \"{col_size}\" {outf}"
        print("Running: " + cmd)
        runcmd(cmd,1,2)

def copy_header(header_file, image_file):
    cmd = f"imgcpinfo {header_file} {image_file}" # overwrites previous output
    print("Running: " + cmd)
    runcmd(cmd,1,2)


# Ensure user inputs are present
if len(argv) != 3:
    print("Usage: post_process_simind activity frameDuration")
    print("\nPost-processes SIMIND outputs to convert from units of cps/MBq to counts.")
    print("This is done by multiplying the projections by a desired activity (MBq) and frame duration (s).")
    print("Finally, the data has Poisson noise added and downsampled versions of the files are saved.")
    exit(1)

# Retrieve user input
activity_MBq = float(argv[1])
frame_duration_s = float(argv[2])

# Define the pattern to match filenames starting with "sim" and ending with 'w' followed by two digits and with '.avg.im'
pattern_re = re.compile(r"sim.*w(\d{2})\.avg\.im")
pattern_txt = "sim*w??.avg.im"
match_group = 1

# Check if the first output file exists and exit if so
if exists("combined.avg.w01.im") or exists("prj.nf.avg.w01.im") or exists("prj.n.avg.w01.im"):
    print("Output files already exist. Exiting to prevent overwritting")
    exit(1)

# Detect if only 1 seed exists by counting the .avg files
if len(glob(pattern_txt)) < 1:
    # Change patterns to not search for averaged images but for raw seed outputs
    pattern_re = re.compile(r"sim.*_(\d*)\.w(\d{2})\.im")
    pattern_txt = "sim*w??.im"
    match_group = 2

    # Initialize a list to store the extracted numbers
    seed_numbers = []

    # Iterate over files in the current directory
    for filename in glob(pattern_txt):
        match = pattern_re.search(filename)
        if match:
            seed_number = int(match.group(1))
            seed_numbers.append(seed_number)
    
    # Find min and max number if any were found
    min_seed = min(seed_numbers)
    max_seed = max(seed_numbers)
    
    if min_seed != max_seed:
        print("More than one seed found but no averaged images found. Running avg_done_sims.py")
        cmd = "./avg_done_sims.py"
        runcmd(cmd,1)
        waitall()

        # Reset search terms
        pattern_re = re.compile(r"sim.*w(\d{2})\.avg\.im")
        pattern_txt = "sim*w??.avg.im"
        match_group = 1
    else:
        print("No averaged images found. Continuing with single seed")

# Initialize a list to store the extracted numbers
window_numbers = []

# Iterate over files in the current directory
for filename in glob(pattern_txt):
    match = pattern_re.search(filename)
    if match:
        window_number = int(match.group(match_group))
        window_numbers.append(window_number)

# Find max number if any were found
max_window = max(window_numbers)
min_window = min(window_numbers)

# Create range of numbers to index
window_range = list(range(min_window, max_window + 1))

for i in window_range:
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
    
    # Loop over every file and sum
    for file in files:
        try:
            pix = npi.ArrayFromIm(file)
        except npi.error:
            print(f"error reading {file}")
            print("   skipping")
            continue
        if num_summed == 0:
            sum = pix.astype(np.float64)
        else:
            sum += pix.astype(np.float64)
        num_summed += 1

    # Write outputs
    sum_outf = f"combined.avg.w{num_txt}.im"
    scaled_outf = f"prj.nf.avg.w{num_txt}.im"
    noise_outf = f"prj.n.avg.w{num_txt}.im"
    if num_summed <= 1:
        print("Summed 1 or fewer images for {outf}: no output generated")
    else:
        # Save the combined radionuclide/VOI image
        print(f"Saving {sum_outf}. Summed {num_summed} images")
        npi.ArrayToIm(sum.astype(np.float32), sum_outf)
        
        # Copy header from a simulation output from the current window to the summed output
        copy_header(files[0], sum_outf)

        # Scale summed image
        scaled_sum = sum * activity_MBq * frame_duration_s

        # Save the scaled summed image as noise free projections
        print(f"Saving {scaled_outf}")
        npi.ArrayToIm(scaled_sum.astype(np.float32), scaled_outf)

        # Copy header from summed output to scaled summed output
        copy_header(sum_outf,scaled_outf)

        # Generate noisey projections
        if exists(noise_outf):
            # Remove noisey projection if it exists
            cmd = f"rm {noise_outf}"
            print("Running: " + cmd)
            runcmd(cmd,1,2)
        cmd = f"addnoise -i {scaled_outf} {noise_outf}"
        print("Running: " + cmd)
        runcmd(cmd,1,2)

        # Downsample noise free and noisey projections
        reduce_proj_to_128(scaled_outf)
        reduce_proj_to_128(noise_outf)

exit(0)
