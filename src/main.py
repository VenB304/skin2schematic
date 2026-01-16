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
    print("Initializing Rig...")
    rig = RigFactory.create_rig(model_type=model)
    
    # Apply Pose
    print(f"Applying pose: {args.pose}")
    pose_data = {}
    if args.pose == "standing":
        pose_data = PoseApplicator.get_standing_pose()
    elif args.pose == "tpose":
        pose_data = PoseApplicator.get_t_pose()
    elif args.pose.endswith(".json"):
        if os.path.exists(args.pose):
            with open(args.pose, 'r') as f:
                pose_data = json.load(f)
        else:
            print(f"Warning: Pose file {args.pose} not found. Using standing.")
    
    PoseApplicator.apply_pose(rig, pose_data)
    
    print("Rasterizing geometry (Inverse Mapping)...")
    pixel_blocks = Rasterizer.rasterize(rig.get_parts(), skin_img)
    print(f"Generated {len(pixel_blocks)} solid blocks.")

    # --- Color Matching ---
    print(f"Matching colors (Palette: {args.palette})...")
    matcher = ColorMatcher(mode=args.palette)
    
    # Using 'rig.root.name' or input name for schematic
    schem_name = f"Statue_{os.path.basename(args.input).split('.')[0]}" if "http" not in args.input else "Statue_Skin"
    builder = SchematicBuilder(name=schem_name)
    
    added_count = 0
    # Basic caching for performance
    color_cache = {}
    
    for pb in pixel_blocks:
        c_key = (pb.r, pb.g, pb.b, pb.a)
        if c_key in color_cache:
            block_id = color_cache[c_key]
        else:
            block_id = matcher.find_nearest(pb.r, pb.g, pb.b, pb.a)
            color_cache[c_key] = block_id
            
        if block_id:
            builder.add_block(pb.x, pb.y, pb.z, block_id)
            added_count += 1
            
    print(f"Mapped {added_count} blocks.")

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
