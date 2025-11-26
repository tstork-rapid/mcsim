#! /usr/bin/env python3
from os.path import exists
from sys import exit, argv
from glob import glob
import numpy as np
import NumpyIm as npi
import subprocess


# Ensure a keV was input by the user
if len(argv) > 1 :
    print("Usage: create_atn.py")
    print("Uses SIMIND attenuation map to make attenuation maps for osem (downsampled to 128x128x128 if needed)")
    print("MUST HAVE INDEX 22 IN SIMIND.INI SET TO 3")
    exit(1)

# Check if SIMIND density map exists
atn_map_txt = "*.hct"
atn_map_files = glob(atn_map_txt)
if len(atn_map_files) < 1:
    print("No attenuation map found")
    exit(1)
elif len(atn_map_files) > 1:
    print("More than one attenuation map found, using " + atn_map_files[0])

# Convert .hct/.ict to .im
atn_map_file = atn_map_files[0]
subprocess.call(["imgconv", "-r", atn_map_file, "simind_atn_map.im"])

# Load attenuation map
pix = npi.ArrayFromIm("simind_atn_map.im")

# Get bin width
pixel_size = subprocess.check_output(["imghdr", "-i", "Pixel Size", atn_map_file])
bin_width = pixel_size.decode('ascii').strip().split(" ")

# Rotate CT -90 degrees about Z axis
#pix = np.rot90(pix, k=3, axes=(1, 2))

# Save attenuation map as .im
npi.ArrayToIm(pix.astype(np.float32), "temp.im")

# Reduce attenuation map to 128x128x128 if necessary
shape = pix.shape
x_factor = shape[2] / 128
y_factor = shape[1] / 128
z_factor = shape[0] / 128
new_bin_width = float(bin_width[0]) * x_factor

if shape[0] != 128 or shape[1] != 128 or shape[2] != 128:
    print("Downsampling attenuation map")
    if exists("temp_128.im"):
        print("Removing previous temp_128.im")
        subprocess.call(["rm", "temp_128.im"])

    subprocess.call(["collapse3d", "-a", str(x_factor), str(y_factor), str(z_factor), "temp.im", "temp_128.im"])

    atn_name = "temp_128.im"
else:
    print("No downsampling needed")
    atn_name = "temp.im"

# Convert attenuation map from linear attenuation/cm to attenuation per voxel
pix = npi.ArrayFromIm(atn_name)
pix = pix * new_bin_width / 10
npi.ArrayToIm(pix.astype(np.float32), "atn.im")

# Update pixel spacing rows and columns in header
subprocess.call(["imsetinfo", "-i", "Pixel Spacing Rows", str(new_bin_width), "-i", "Pixel Spacing Cols", str(new_bin_width), "-i", "Slices Spacing", str(-1 * new_bin_width), "-i", "Modality", "CT", "atn.im"])

# Create symbolic links
if exists("atn.w1i1.im"):
    subprocess.call(["rm", "atn.w1i1.im"])

subprocess.call(["ln", "-s", "atn.im", "atn.w1i1.im"])

if exists("atn.w1i2.im"):
    subprocess.call(["rm", "atn.w1i2.im"])

subprocess.call(["ln", "-s", "atn.im", "atn.w1i2.im"])

# Remove temp .im images
temp_files = glob("temp*.im")
subprocess.call(["rm", *temp_files])
