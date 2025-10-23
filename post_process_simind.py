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
if len(argv) != 2:
    print("Usage: post_process_simind.py parameter_file.par")
    print("\nPost-processes SIMIND outputs to convert from units of cps/MBq to counts.")
    print("First, all seeds are averaged into *.avg* files by avg_done_sims.py")
    print("Second, all radionuclides for a given VOI and window are summed into *_all_* files")
    print("Third, each *_all_* file is scaled by a desired activity (MBq) and frame duration (s)")
    print("Fourth, all VOIs for a given window are summed into prj.nf.* files")
    print("Fifth, all prj.nf.* files have noise added to them to prj.n.* files")
    print("Lastly, all prj.* files are collapsed to 128x128")
    exit(1)

# Retrieve user input
par_file = argv[1]
if not exists(par_file):
    print(f"No {par_file} was found")
    exit(1)
else:
    # Open parameter file
    inf = open(par_file,'r')

    # Create dictionary of VOI and activity
    obj_dict = {}
    for line in inf:
        line = re.sub('#.*', '',line).strip()
        if len(line) == 0: 
            continue
        k, v = line.split('=')
        obj_dict[k.strip()] = v.strip()

# Extract the frame duration from the dictionary
try:
    frame_duration_s = float(obj_dict['frame duration'])
except:
    print(f"No \"frame duration\" key was found in {par_file}")
    exit(1)

# Define the pattern to match filenames
pattern_re = re.compile(r"sim_(\w{1,2}\d{1,3})_(.*).w(\d{2})\.avg\.im")
pattern_txt = "sim*w??.avg.im"

# Check if the first output file exists and exit if so
if exists("prj.nf.w01.im") or exists("prj.n.w01.im"):
    print("Output files already exist. Exiting to prevent overwritting")
    exit(1)

# Detect if any .avg files exist
if len(glob(pattern_txt)) < 1:
    # Change patterns to not search for averaged images but for raw seed outputs
    pattern_re = re.compile(r"sim.*_(\d*)\.w(\d{2})\.im")
    pattern_txt = "sim*w??.im"

    # Initialize a list to store the extracted seed numbers
    seed_numbers = []

    # Iterate over files in the current directory
    for filename in glob(pattern_txt):
        match = pattern_re.search(filename)
        if match:
            seed_number = int(match.group(1))
            seed_numbers.append(seed_number)
    
    # Find min and max seed numbers
    min_seed = min(seed_numbers)
    max_seed = max(seed_numbers)
    
    if min_seed != max_seed:
        print("More than one seed found but no averaged images found. Running avg_done_sims.py")
        cmd = "./avg_done_sims.py"
        runcmd(cmd,1)
        waitall()

        # Reset search terms
        pattern_re = re.compile(r"sim_(\w{1,2}\d{1,3})_(.*).w(\d{2})\.avg\.im")
        pattern_txt = "sim*w??.avg.im"
    else:
        print("No averaged images found. Continuing with single seed")

# Initialize a list to store the extracted window numbers and vois
radionuclides = []
vois = []
window_numbers = []

# Iterate over files in the current directory
for filename in glob(pattern_txt):
    match = pattern_re.search(filename)
    if match:
        radionuclide = match.group(1)
        radionuclides.append(radionuclide)
        
        voi = match.group(2)
        vois.append(voi)
        
        window_number = int(match.group(3))
        window_numbers.append(window_number)

# Remove duplicates from string lists
radionuclides = list(set(radionuclides))
vois = list(set(vois))

# Find max and min window numbers
max_window = max(window_numbers)
min_window = min(window_numbers)

# Create range of window numbers to index
window_range = list(range(min_window, max_window + 1))

# Loop through each window, each voi, each radionuclide
for i in window_range:
    # Create window number as text
    if i < 10:
        num_txt = "0" + str(i)
    else:
        num_txt = str(i)

    num_summed_outer = 0
    combined_scaled_outf = f"prj.nf.w{num_txt}.im"
    noise_outf = f"prj.n.w{num_txt}.im"
    for voi in vois:
        num_summed_inner = 0
        sum_outf = f"sim_all_{voi}.w{num_txt}.im"

        for radionuclide in radionuclides:
            file_name = f"sim_{radionuclide}_{voi}.w{num_txt}.avg.im"
            
            # Combine all radionuclides in a given VOI in a given window
            try:
                pix = npi.ArrayFromIm(file_name)
            except npi.error:
                print(f"error reading {file_name}")
                print("   skipping")
                continue

            if num_summed_inner == 0:
                sum = pix.astype(np.float64)
            else:
                sum += pix.astype(np.float64)
            num_summed_inner += 1
        
        # Save combined radionuclide images
        print(f"Summed {num_summed_inner} radionuclides for {voi} window {num_txt}")
        print(f"    Saving {sum_outf}")
        npi.ArrayToIm(sum.astype(np.float32), sum_outf)

        # Copy header from last non-combined radionuclide file to the combined
        copy_header(file_name, sum_outf)

        # Scale summed image
        try:
            activity_MBq = float(obj_dict[voi])
        except:
            print(f"No \"{voi}\" key in {par_file}")
            exit(1)
        print(f"Scaling {sum_outf} by {activity_MBq} MBq and {frame_duration_s} seconds")
        scaled_sum = sum * activity_MBq * frame_duration_s

        # Combine VOIs for a given window
        if num_summed_outer == 0:
            combined_scaled_sum = sum.astype(np.float64)
        else:
            combined_scaled_sum += sum.astype(np.float64)
        num_summed_outer += 1

    print(f"Combined {num_summed_outer} scaled VOIs for window {num_txt}")
    print(f"    Saving {combined_scaled_outf}")
    npi.ArrayToIm(combined_scaled_sum.astype(np.float32), combined_scaled_outf)

    # Copy header from summed output to scaled summed output
    copy_header(sum_outf, combined_scaled_outf)

    # Write the frame duration to the header
    cmd = f"imsetinfo -i \"Actual Frame Duration\" \"{frame_duration_s*1000}\" {combined_scaled_outf}"
    print("Running: " + cmd)
    runcmd(cmd,1,2)

    # Generate the noisey projections
    if exists(noise_outf):
        # Remove noisey projection if it exists
        cmd = f"rm {noise_outf}"
        print("Running: " + cmd)
        runcmd(cmd,1,2)
    cmd = f"addnoise -i {combined_scaled_outf} {noise_outf}"
    print("Running: " + cmd)
    runcmd(cmd,1,2)

    # Downsample the noise free and noisey projections
    reduce_proj_to_128(combined_scaled_outf)
    reduce_proj_to_128(noise_outf)
    print("\n")

exit(0)