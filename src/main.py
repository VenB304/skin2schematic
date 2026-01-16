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
    parser.add_argument("-p", "--palette", choices=["mixed", "concrete", "wool", "terracotta"], default="mixed", help="Block palette to use")
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
    color_cache = {}
    
    total_added = 0
    
    # Dynamic Spacing Logic
    last_max_x = None
    GAP_SIZE = 5
    
    for idx, (pose_name, pose_data) in enumerate(poses_to_generate):
        print(f"[{idx+1}/{len(poses_to_generate)}] Processing Pose: {pose_name}")
        
        # New rig for each pose to ensure clean state
        rig = RigFactory.create_rig(model_type=model)
        PoseApplicator.apply_pose(rig, pose_data)
        
        blocks = Rasterizer.rasterize(rig.get_parts(), skin_img)
        
        if not blocks:
            continue
            
        # --- Auto-Grounding ---
        # Find Min Y
        min_y = min(b.y for b in blocks)
        shift_y = -min_y
        
        # Apply Shift
        # We can update the PixelBlock objects directly or apply during adding.
        # Let's apply during adding/bounds calc.
        
        # Calculate local bounds (With Shift Applied)
        local_min_x = min(b.x for b in blocks)
        local_max_x = max(b.x for b in blocks)
        
        # Determine Offset
        if last_max_x is None:
            # First statue.
            offset_x = 0
        else:
            # We want current_min_x (post-shift) = last_max_x + GAP
            offset_x = last_max_x + GAP_SIZE - local_min_x
            
        # Update bounds tracker for next iteration
        last_max_x = local_max_x + offset_x
        
        for pb in blocks:
            c_key = (pb.r, pb.g, pb.b, pb.a)
            if c_key in color_cache:
                block_id = color_cache[c_key]
            else:
                block_id = matcher.find_nearest(pb.r, pb.g, pb.b, pb.a)
                color_cache[c_key] = block_id
                
            if block_id:
                # Add X offset & Y Shift
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
