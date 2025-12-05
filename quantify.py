#! /usr/bin/env python3
from os.path import exists
from sys import exit, argv
import numpy as np
import NumpyIm as npi
import subprocess
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from scipy import ndimage as ndi
from skimage import filters

def threshold_2D_and_3D(pix, debug=False):
    """
    Uses Otsu's method to determine the threshold between the foreground and background of 2D/3D image data.

    Args:
        pix: 2D NumPy array (Y, X) representing the image volume
        debug: boolean

    Returns:
        binary_pix: 2D binary array representing the thresholded image volume
    """

    # Threshold image
    otsu_threshold = filters.threshold_otsu(pix)

    if otsu_threshold == 0:
        print("Otsu threshold failed. Use debug mode to investigate. Skipping this image for radii calculation")
        otsu_threshold = np.max(pix)-1 # Set threshold to max pixel to make a very small radii, which effectively tosses this image out later (since we use the max radius across all images)

    binary_pix = pix > otsu_threshold
    print(f"Threshold value = {otsu_threshold}") if debug else None

    # Binary closing
    ndi.binary_closing(binary_pix, iterations=5, output=binary_pix)

    return binary_pix

def find_sphere_centers(pix, binary_mask, n_spheres=1, min_voxels=9):
    """
    Compute intensity-weighted centers of mass (COM) for each connected component in a binary mask,
    then return up to n_spheres centers with the highest total activity.

    Args:
        pix: 3D numpy array (Z, Y, X), grayscale
        binary_mask: 3D numpy array (Z, Y, X), 0/1
        n_spheres: int, maximum number of spheres to return
        min_voxels: int, minimum component size in voxels to keep
    Returns:
        List of (z, y, x) float centers (COM).
    """
    shape = pix.shape
    if len(shape) == 2:
        # PSEN data
        data_3D = False
        structure = np.ones((3, 3), dtype=bool)
    else:
        # Recon data
        data_3D = True
        structure = np.ones((3, 3, 3), dtype=bool)  # 26-connectivity

    # Label connnected components in the binary mask
    labels, nlab = ndi.label(binary_mask.astype(bool), structure=structure)

    # If no components were found, return an empty list early
    if nlab == 0:
        return []

    # Prepare a "safe" copy of the grascale volume to use as weights
    vol_safe = np.nan_to_num(pix.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)

    # Compute component sizes by counting label occurrences
    sizes = np.bincount(labels.ravel())

    # Collect tuples of (total_intensity, center) for each kept component
    entries = [] # unknown length of final array
    for lab in range(1, nlab + 1):
        # Get size of this component if 'lab' is within the array bounds of 'sizes', otherwise fall back to computing by comparison
        size = int(sizes[lab]) if lab < sizes.size else int((labels == lab).sum())

        # Skip components that are smaller than the minimum threshold
        if size < min_voxels:
            continue

        # Intensity-weighted COM within the component
        if data_3D:
            cz, cy, cx = ndi.center_of_mass(vol_safe, labels=labels, index=lab)
        else:
            cy, cx = ndi.center_of_mass(vol_safe, labels=labels, index=lab)
        
        # Total activity inside this component
        total_intensity = float(vol_safe[labels == lab].sum())

        if data_3D:
            entries.append((total_intensity, (cz, cy, cx)))
        else:
            entries.append((total_intensity, (cy, cx)))

    # Sort by total activity and keep top 'n_spheres'
    entries.sort(key=lambda t: t[0], reverse=True)

    # Return the COMs for the top 'n_spheres' components
    return [c for _, c in entries[:n_spheres]]

def get_spacing(file_name):
    """
    Get the Z, Y, X spacing of the image data.

    Args:
        file_name: file location of the image data file

    Returns:
        spacing: array of the image spacing in (Z, Y, X)
    """

    try:
        spacing = subprocess.check_output(["imghdr", "-i", "Pixel Size", file_name]) # in mm
        spacing = spacing.decode('ascii').strip().split(" ")
        spacing.reverse() # convert from X/Y/Z to Z/Y/X 
        spacing = [float(s) for s in spacing] # convert to float

        if spacing == [0, 0, 0]:
            raise Exception
    except:
        print("Could not determine pixel spacing from data.")
        spacing = input("Enter square voxel dimension in mm: ")
        spacing = [float(spacing)] * 3

    return spacing

def compute_radii_from_binary_3D(binary_mask, centers, spacing, debug=False):
    """
    Return radii (in mm) for each center, in the same order as `centers`

    Args:
        binary_mask : 3D numpy array (Z,Y,X), 0/1
        centers     : iterable of (z, y, x) floats (same indexing as the array)
        spacing     : (dz, dy, dx) voxel spacing in mm

    Returns:
        radii_mm : list of float radii in mm, same length/order as `centers`.
    """
    # Fix negative z for this function
    spacing = [abs(s) for s in spacing]

    # Create a boolean foreground mask 
    mask = binary_mask.astype(bool)

    # Label connected components
    structure = np.ones((3, 3, 3), dtype=int)
    labeled, num_features = ndi.label(mask, structure=structure)

    radii_mm = np.empty(len(centers), dtype=float)
    for i, c in enumerate(centers):
        c_vox = tuple(int(round(v)) for v in c) # round center to nearest voxel
        lbl = labeled[c_vox] # get the label at the center
        erroded = ndi.binary_erosion(mask, structure=structure, border_value=0) # errode the mask
        comp = (labeled == lbl) # get component
        shell = comp & (~erroded) # compute XOR of component and errosion
        idxs = np.array(np.nonzero(shell)).T

        diffs = (idxs - c) * np.array(spacing)
        dists = np.linalg.norm(diffs, axis=1)
        print(f"Radii values = Max: {dists.max()}, Mean: {dists.mean()}, Min: {dists.min()}") if debug else None
        radii_mm[i] = round(dists.max(), 3) # use the max radius to get all voxels in the component, rounded to 3 decimals

    return radii_mm

def sum_voxels_in_sphere(array, center, radius):
    """
    Sum voxel values within a sphere of given center and radius.
    
    Parameters:
        array (ndarray): 3D array of voxel intensities.
        center (tuple): (cx, cy, cz) coordinates of sphere center.
        radius (float): Sphere radius in voxel units.
    
    Returns:
        float: Sum of voxel values inside the sphere.
    """

    # Generate 3D grid of voxel coordinates
    z, y, x = np.indices(array.shape)

    # Compute Euclidean distance from each voxel to the center
    distances = np.sqrt((x - center[0])**2 +
                        (y - center[1])**2 +
                        (z - center[2])**2)
    
    # Create mask for voxels inside the sphere
    mask = distances <= radius

    # Sum voxel values where mask is True
    return array[mask].sum()

def display_circles_3D(pix, center, radius):
    """
    Display orthogonal views (axial, sagittal, coronal) of a 3D volume and overlay
    a circle of a given radius centered at `center`.

    Inputs:
        pix    : 3D NumPy array shaped (Z, Y, X). Index order is (z, y, x).
        center : iterable (z, y, x) center coordinates (floats or ints) in voxel units.
        radius : float, radius of the circle in voxel units (assumes isotropic voxels).

    Returns:
        None
    """

    # Get center values
    z = center[0]
    y = center[1]
    x = center[2]

    # Convert center values to integer indices for slicing
    zi = int(round(center[0]))
    yi = int(round(center[1]))
    xi = int(round(center[2]))
    
    # Extract slices for 3 views
    axial_slice = pix[zi, :, :]
    sagittal_slice = pix[: , :, xi]
    coronal_slice = pix[:, yi, :]

    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(15,5))

    # Axial view
    im0 = axes[0].imshow(axial_slice, cmap='gray', origin='upper')
    axes[0].set_title(f"Axial (Z={zi})")
    circle_axial = Circle((x, y), radius, color='red', alpha=0.5, fill=False, linewidth=2)
    axes[0].add_patch(circle_axial)
    fig.colorbar(im0, ax=axes[0])

    # Sagittal view
    im1 = axes[1].imshow(sagittal_slice, cmap='gray', origin='upper')
    axes[1].set_title(f"Sagittal (X={xi})")
    circle_sagittal = Circle((y, z), radius, color='red', alpha=0.5, fill=False, linewidth=2)
    axes[1].add_patch(circle_sagittal)
    fig.colorbar(im1, ax=axes[1])

    # Coronal view
    im2 = axes[2].imshow(coronal_slice, cmap='gray', origin='upper')
    axes[2].set_title(f"Coronal (Y={yi})")
    circle_coronal = Circle((x, z), radius, color='red', alpha=0.5, fill=False, linewidth=2)
    axes[2].add_patch(circle_coronal)
    fig.colorbar(im2, ax=axes[2])

    # Display the centroid with a circle of calculated radius
    plt.tight_layout()
    plt.show()

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
    # Calculate radius of sphere (assumes isotopric voxels)
    binary_pix = threshold_2D_and_3D(pix, False)
    centers = find_sphere_centers(pix, binary_pix, 1)
    spacing = get_spacing(recon)
    radii_mm = compute_radii_from_binary_3D(binary_pix, centers, spacing, False)
    radii_pix = [r / abs(spacing[2]) for r in radii_mm]

    print(f"Calculated radius = {radii_mm[0]} mm / {radii_pix[0]} px")

    # Ask for confirmation on radius
    accepted = False
    while accepted == False:
        display_circles_3D(pix, centers[0], radii_pix[0])
        response = input("Is the VOI acceptable (Y/N)? ")
        if response == 'Y' or response == 'y':
            accepted = True
        elif response == 'N' or response == 'n':
            radii_pix[0] = float(input("Enter in the new radius in px: "))
        else:
            print("Unknown response, please answer Y or N.")

    # Sum the in the sphere
    tot_counts = sum_voxels_in_sphere(pix, centers[0], radii_pix[0])
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