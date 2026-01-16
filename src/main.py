import argparse
import sys
import os
import json

# Adjust path to find modules if running from src directly
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from skin_loader import SkinLoader
from color_matching import ColorMatcher
from schematic_builder import SchematicBuilder

# New Geometry System
from geometry.rig import RigFactory
from geometry.pose import PoseApplicator
from geometry.rasterizer import Rasterizer

def main():
    parser = argparse.ArgumentParser(description="Convert Minecraft skin to Litematic statue.")
    parser.add_argument("input", help="Skin source: File path, URL, or Username")
    parser.add_argument("-o", "--output", help="Output file path (default: input_name.litematic)")
    parser.add_argument("-p", "--palette", choices=["all", "wool", "concrete", "terracotta"], default="all", help="Block palette to use")
    parser.add_argument("--solid", action="store_true", help="Disable hollow optimization (fill internal blocks)")
    parser.add_argument("-m", "--model", choices=["auto", "classic", "slim"], default="auto", help="Skin model type")
    parser.add_argument("--pose", help="Pose name (standing, tpose) or path to JSON file", default="standing")

    args = parser.parse_args()

    print(f"Loading skin from: {args.input}")
    try:
        skin_img = SkinLoader.load_skin(args.input)
    except Exception as e:
        print(f"Error loading skin: {e}")
        sys.exit(1)

    model = args.model
    if model == "auto":
        model = SkinLoader.detect_model(skin_img)
        print(f"Detected model: {model}")
    else:
        print(f"Using model: {model}")

    # --- New Geometry Pipeline ---
    
    poses_to_generate = []
    
    if args.pose == "debug_all":
        print("Debug Mode: Generating all poses...")
        # Sort keys for consistent order
        for name in sorted(PoseApplicator.POSES.keys()):
            poses_to_generate.append((name, PoseApplicator.get_pose(name)))
    elif args.pose in PoseApplicator.POSES:
        poses_to_generate.append((args.pose, PoseApplicator.get_pose(args.pose)))
    elif args.pose.endswith(".json"):
        if os.path.exists(args.pose):
            with open(args.pose, 'r') as f:
                pose_data = json.load(f)
            poses_to_generate.append((args.pose, pose_data))
        else:
            print(f"Warning: Pose file {args.pose} not found. Using default.")
            poses_to_generate.append(("default", PoseApplicator.get_standing_pose()))
    else:
        print(f"Warning: Unknown pose '{args.pose}'. Using default.")
        poses_to_generate.append(("default", PoseApplicator.get_standing_pose()))

    # Initialize Components
    
    # We want a single builder if debug_all?
    # Yes, "generate all available poses in a single .litematic".
    
    schem_name = f"Statue_{os.path.basename(args.input).split('.')[0]}" if "http" not in args.input else "Statue_Skin"
    if args.pose == "debug_all":
        schem_name += "_Gallery"
        
    builder = SchematicBuilder(name=schem_name)
    matcher = ColorMatcher(mode=args.palette)
    
    # Optimization 1: Pre-compute color cache
    print("Pre-computing color palette...")
    color_cache = matcher.map_unique_colors(skin_img)
    print(f"Cached {len(color_cache)} unique colors.")
    
    GAP_SIZE = 5
    last_max_x = None
    total_added = 0
    
    # Process Poses
    for idx, (pose_name, pose_data) in enumerate(poses_to_generate):
        print(f"[{idx+1}/{len(poses_to_generate)}] Processing Pose: {pose_name}")
        
        rig = RigFactory.create_rig(model_type=model)
        PoseApplicator.apply_pose(rig, pose_data)
        
        # Optimization 2 & 3 inside Rasterizer (Vectorized, Early Culling)
        blocks = Rasterizer.rasterize(rig.get_parts(), skin_img, solid=args.solid)
        
        if not blocks:
            continue
            
        # --- Auto-Grounding ---
        min_y = min(b.y for b in blocks)
        shift_y = -min_y
        
        local_min_x = min(b.x for b in blocks)
        local_max_x = max(b.x for b in blocks)
        
        if last_max_x is None:
            offset_x = 0
        else:
            offset_x = last_max_x + GAP_SIZE - local_min_x
            
        last_max_x = local_max_x + offset_x
        
        # --- Hollow Logic ---
        # With new Vectorized Forward Mapping Rasterizer, 
        # default output is already a "Shell" (Hollow-like) because we map surface pixels.
        # If args.solid is False, we rely on nature of Forward Mapping to be hollow-ish.
        # However, Rasterizer handles Surface mapping.
        # So we don't need the expensive "Neighbor Check" anymore!
        # This is a huge optimization (O(N) -> O(1) per block).
        # We implicitly get hollow result.
        # If users want strictly "No Internal Blocks", the new rasterizer naturally provides that.
        # So we can remove the 'Hollow Logic' block entirely here.
        # Wait, if Rasterizer provides a Shell, and we verify neighbors, it would just confirm it.
        # Disabling legacy Hollow Logic check for speed.
        
        # --- Sign Placement (Debug Gallery Only) ---
        if args.pose == "debug_all":
            # Place sign in front. 
            # Center X = (min_x + max_x) // 2
            # Front Z = min_z - 2? (Assuming Z+ is back?)
            # Rig coordinates: Z+ is Back (Right Hand Rule match). Z- is Front.
            # So Min Z is the front-most face. Place sign at Min Z - 2.
            center_x_local = (local_min_x + local_max_x) // 2
            front_z_local = min(b.z for b in blocks) - 2
            
            final_sign_x = int(center_x_local + offset_x)
            final_sign_y = int(shift_y) # Floor level
            final_sign_z = int(front_z_local)
            
            # Add to builder
            builder.add_sign(
                final_sign_x, final_sign_y, final_sign_z, 
                text=pose_name, 
                wall_sign=False, 
                facing="north" # Facing North means text is on South side? Or facing towards North?
                               # Standard Sign: Rotation needed to face camera looking at statue.
                               # Statue looks South (-Z is front? No, usually +Z is South in MC).
                               # Let's try default "north" (Rotation 8) or similar.
                               # Actually, if Z- is front, we are looking at it from -Z towards +Z.
                               # So sign should face -Z (North).
            )

        for pb in blocks:
            c_key = (pb.r, pb.g, pb.b, pb.a)
            if c_key in color_cache:
                block_id = color_cache[c_key]
            else:
                block_id = matcher.find_nearest(pb.r, pb.g, pb.b, pb.a)
                color_cache[c_key] = block_id
                
            if block_id:
                builder.add_block(pb.x + int(offset_x), pb.y + int(shift_y), pb.z, block_id)
                total_added += 1
                
    print(f"Total blocks mapped: {total_added}")

    output_path = args.output
    if not output_path:
        base_name = os.path.basename(args.input)
        if '.' in base_name:
            base_name = base_name.rsplit('.', 1)[0]
        if "http" in args.input:
            base_name = "downloaded_statue"
        
        # Create output directory: "[skin_name] output"
        output_dir = f"{base_name} output"
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError:
            pass # Fail silently if we can't create dir, fallback to current dir? 
                 # Or just let open() fail later. exist_ok handles common case.
        
        output_path = os.path.join(output_dir, f"{base_name}_{args.pose}.litematic")

    print(f"Saving to {output_path}...")
    try:
        builder.save(output_path)
    except Exception as e:
        print(f"Error saving schematic: {e}")
        sys.exit(1)

    print("Done!")

if __name__ == "__main__":
    main()
