#! /usr/bin/env python3
from os.path import exists
from sys import exit, argv
import numpy as np
import NumpyIm as npi
import subprocess
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

def fit_sphere(points, weights=None):
    # points: Nx3 array of (x, y, z)
    A = np.hstack((2*points, np.ones((points.shape[0], 1))))
    f = np.sum(points**2, axis=1)
    if weights is not None:
        W = np.diag(weights)
        A = W @ A
        f = W @ f
    c, *_ = np.linalg.lstsq(A, f, rcond=None)
    center = c[:3]
    radius = np.sqrt(np.sum(center**2) + c[3])
    return center, radius

def sum_voxels_in_sphere(array, center, radius):
    # center = (cx, cy, cz)
    z, y, x = np.indices(array.shape)
    distances = np.sqrt((x - center[0])**2 +
                        (y - center[1])**2 +
                        (z - center[2])**2)
    mask = distances <= radius
    return array[mask].sum()

# Ensure user inputs are present
if len(argv) != 4 and len(argv) != 5:
    print("Usage: quantify.py CF projection_file recon_file outfile")
    print("\nCF: conversion factor for the image in cps/MBq")
    print("To use the calibration mode, enter a CF of 0 or smaller and do not specify an outfile")
    exit(1)

# Retrieve user input
CF = float(argv[1])
if CF <= 0:
    print("---Calibration mode---")
    calibration_mode = True
else:
    calibration_mode = False
    outf = argv[4]
proj = argv[2]
recon = argv[3]

# Check to make sure the files exist
if not exists(proj) or not exists(recon):
    print("Infiles do not exist!")
    exit(1)

# Read in the infile (assumes units of counts)
pix = npi.ArrayFromIm(recon)

# Get the frame duration from projections
hdr = subprocess.check_output(["header", "-i", proj])
hdr = hdr.decode('ascii').strip().split("\n")
try:
    frame_duration_txt = [item for item in hdr if "Actual Frame Duration" in item]
    frame_duration = frame_duration_txt[0].split("\t")
    frame_duration = float(frame_duration[-1]) / 1000 # convert to seconds
    print(f"Found frame duration of {frame_duration} seconds in header")
except:
    print("No frame duration found in header")
    frame_duration = float(input("Enter the frame duration in seconds: "))

# Get the total number of frames
try:
    num_frames_txt = [item for item in hdr if "Number of Projections" in item]
    num_frames = num_frames_txt[0].split("\t")
    num_frames = int(num_frames[-1])
    print(f"Found {num_frames} frames in header")
except:
    print("No number of projections found in header")
    num_frames = int(input("Enter the number of projections: "))

if calibration_mode:
    # Compute centroid
    centroid = subprocess.check_output(["centroid", recon])
    centroid = centroid.decode('ascii').strip().split("\t")
    centroid_x = round(float(centroid[-3]))
    centroid_y = round(float(centroid[-2]))
    centroid_z = round(float(centroid[-1]))
    print(f"Centroid found at {centroid_x}, {centroid_y}, {centroid_z}")
    
    # Calculate radius of sphere
    mean = pix.mean()
    std = pix.std()
    threshold = mean + 2 * std
    #threshold = np.percentile(pix, 98) # causes slow processing
    coords = np.argwhere(pix > threshold)  # pick voxels above threshold
    weights = pix[tuple(coords.T)]         # intensity as weight
    center, radius = fit_sphere(coords, weights)
    print(f"Calculated radius = {radius}")

    # Extract slices for 3 views
    axial_slice = pix[centroid_z,:,:]
    sagittal_slice = pix[:,:,centroid_x]
    coronal_slice = pix[:, centroid_y, :]

    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(15,5))

    # Axial view
    im0 = axes[0].imshow(axial_slice, cmap='gray', origin='upper')
    axes[0].set_title(f"Axial (Z={centroid_z})")
    circle_axial = Circle((centroid_x, centroid_y), radius, color='red', alpha=0.5, fill=False, linewidth=2)
    axes[0].add_patch(circle_axial)
    fig.colorbar(im0, ax=axes[0], label="Counts")

    # Sagittal view
    im1 = axes[1].imshow(sagittal_slice, cmap='gray', origin='upper')
    axes[1].set_title(f"Sagittal (X={centroid_x})")
    circle_sagittal = Circle((centroid_z, centroid_y), radius, color='red', alpha=0.5, fill=False, linewidth=2)
    axes[1].add_patch(circle_sagittal)
    fig.colorbar(im1, ax=axes[1], label="Counts")

    # Coronal view
    im2 = axes[2].imshow(coronal_slice, cmap='gray', origin='upper')
    axes[2].set_title(f"Coronal (Y={centroid_y})")
    circle_coronal = Circle((centroid_x, centroid_z), radius, color='red', alpha=0.5, fill=False, linewidth=2)
    axes[2].add_patch(circle_coronal)
    fig.colorbar(im2, ax=axes[2], label="Counts")               

    # Display the centroid with a circle of calculated radius
    plt.tight_layout()
    plt.show()

    # Sum the in the sphere
    tot_counts = sum_voxels_in_sphere(pix, (centroid_x, centroid_y, centroid_z), radius)
    print(f"{tot_counts} counts in image")
        
    activity_MBq = float(input("Enter the activity in MBq: "))

    CF = (tot_counts / (frame_duration * num_frames)) / activity_MBq
    print(f"CF = {CF} cps/MBq")
    exit(1)
else:
    # Convert image to cps
    pix = pix / (frame_duration * num_frames)

    # Get the voxel dimensions
    slice_thickness = subprocess.check_output(["imghdr", "-i", "SliceThickness", recon])
    slice_thickness = slice_thickness.decode('ascii')
    try:
        slice_thickness = float(slice_thickness)
        print(f"Found slice thickness of {slice_thickness} cm in header")
    except:
        print("No slice thickness found in header")
        slice_thickness = float(input("Enter the slice thickness in cm: "))

    pixel_width = subprocess.check_output(["imghdr", "-i", "PixelWidth", recon])
    pixel_width = pixel_width.decode('ascii')
    try:
        pixel_width = float(pixel_width)
        print(f"Found pixel width of {pixel_width} cm in header")
    except:
        print("No pixel width found in header")
        pixel_width = float(input("Enter the pixel width in cm: "))

    # Convert image to cps/mL
    pix = pix / (slice_thickness * pixel_width * pixel_width) # assumes square pixels in the axial direction

    # Convert image to Bq/mL
    pix = pix * (1 / CF) * 1e6

# Save output image
npi.ArrayToIm(pix.astype(np.float32), outf)