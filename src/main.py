import argparse
import sys
import os
import json
import glob
from typing import Optional, List, Tuple

# Adjust path to find modules if running from src directly
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from skin_loader import SkinLoader
from color_matching import ColorMatcher
from schematic_builder import SchematicBuilder

# New Geometry System
from geometry.rig import RigFactory
from geometry.pose import PoseApplicator
from geometry.rasterizer import Rasterizer

def process_skin(input_path: str, output_path: str, model: str, pose_name: str, solid: bool, palette: str, matcher: ColorMatcher, cache: dict) -> bool:
    """
    Process a single skin file. Returns True if successful.
    """
    try:
        try:
            skin_img = SkinLoader.load_skin(input_path)
        except Exception as e:
            print(f"Error loading skin {os.path.basename(input_path)}: {e}")
            return False

        detected_model = model
        if detected_model == "auto":
            detected_model = SkinLoader.detect_model(skin_img)
            # print(f"  Detected model: {detected_model}")
        
        # Get Pose Data
        pose_data = {}
        if pose_name == "debug_all":
            # Handle Debug All separately? 
            # Actually debug_all generates multiple poses in one schematic.
            # But here we are processing one *skin*.
            # If input is a batch of skins, debug_all means each skin gets a gallery?
            # Yes.
            pass
        elif pose_name in PoseApplicator.POSES:
            pose_data = PoseApplicator.get_pose(pose_name)
        else:
            # Check file
            if pose_name.endswith(".json") and os.path.exists(pose_name):
                with open(pose_name, 'r') as f:
                    pose_data = json.load(f)
            else:
               # print(f"  Warning: Unknown pose '{pose_name}'. Using default.")
                pose_data = PoseApplicator.get_standing_pose()

        # Prepare List of Poses to Render
        poses_to_render = []
        if pose_name == "debug_all":
            for name in sorted(PoseApplicator.POSES.keys()):
                poses_to_render.append((name, PoseApplicator.get_pose(name)))
        else:
             poses_to_render.append((pose_name, pose_data))

        # Setup Builder
        base_name = os.path.basename(input_path).rsplit('.', 1)[0]
        schem_name = f"Statue_{base_name}"
        if pose_name == "debug_all":
            schem_name += "_Gallery"
        
        builder = SchematicBuilder(name=schem_name)
        
        # Determine output path if not explicit
        # If output_path is a directory, append filename
        # If output_path is None, use default logic
        final_output = output_path
        if not final_output:
            output_dir = f"{base_name} output"
            os.makedirs(output_dir, exist_ok=True)
            suffix = f"_{pose_name}" if pose_name != "debug_all" else "_debug_all"
            final_output = os.path.join(output_dir, f"{base_name}{suffix}.litematic")
        elif os.path.isdir(final_output) or final_output.endswith(os.sep):
             # Is directory
             os.makedirs(final_output, exist_ok=True)
             suffix = f"_{pose_name}" if pose_name != "debug_all" else "_debug_all"
             final_output = os.path.join(final_output, f"{base_name}{suffix}.litematic")
        
        # Pre-compute unique colors for this skin
        # Verify cache? Caller provided a cache, but that is global?
        # No, color_cache provided by caller might be existing for optimization?
        # Actually each skin has different colors.
        # But matcher.map_unique_colors returns a mapping for THIS image.
        
        skin_color_cache = matcher.map_unique_colors(skin_img)
        
        GAP_SIZE = 5
        last_max_x = None
        total_added = 0
        
        for p_name, p_data in poses_to_render:
            rig = RigFactory.create_rig(model_type=detected_model)
            PoseApplicator.apply_pose(rig, p_data)
            
            blocks = Rasterizer.rasterize(rig.get_parts(), skin_img, solid=solid)
            
            if not blocks:
                continue
                
            # Auto Grounding
            min_y = min(b.y for b in blocks)
            shift_y = -min_y
            
            local_min_x = min(b.x for b in blocks)
            local_max_x = max(b.x for b in blocks)
            
            if last_max_x is None:
                offset_x = 0
            else:
                offset_x = last_max_x + GAP_SIZE - local_min_x
                
            last_max_x = local_max_x + offset_x
            
            # Debug Labels
            if pose_name == "debug_all":
                 front_z_local = min(b.z for b in blocks)
                 sign_z = int(front_z_local - 1)
                 sign_x = int(offset_x)
                 sign_y = 0
                 
                 builder.add_sign(sign_x, sign_y, sign_z, text=p_name, facing="north")
                 # print(f"    [X={sign_x}] Pose: {p_name}")

            for pb in blocks:
                c_key = (pb.r, pb.g, pb.b, pb.a)
                block_id = skin_color_cache.get(c_key)
                if not block_id:
                     block_id = matcher.find_nearest(*c_key)
                     skin_color_cache[c_key] = block_id
                
                if block_id:
                    builder.add_block(pb.x + int(offset_x), pb.y + int(shift_y), pb.z, block_id)
                    total_added += 1

        builder.save(final_output)
        return True
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        import traceback
        traceback.print_exc()
        return False

def interactive_mode():
    print("\n=== Skin2Schematic Wizard ===")
    
    # 1. Scan for Skins
    files = glob.glob("*.png")
    if not files:
        print("No .png files found in current directory.")
        return
        
    print(f"Found {len(files)} skin(s).")
    print("0. All Files")
    for i, f in enumerate(files[:9]):
        print(f"{i+1}. {f}")
    if len(files) > 9:
        print("... and more")
        
    choice = input("Select input (0-9): ").strip()
    selected_files = []
    if choice == "0" or choice.lower() == "all":
        selected_files = files
    elif choice.isdigit() and 1 <= int(choice) <= len(files):
        selected_files = [files[int(choice)-1]]
    else:
        print("Invalid selection.")
        return

    # 2. Select Pose
    print("\nAvailable Poses:")
    print("0. default (Standing)")
    print("1. walking")
    print("2. running")
    print("3. sitting")
    print("4. t_pose")
    print("5. debug_all (Gallery)")
    
    p_choice = input("Select pose (0-5) or type name: ").strip()
    pose_map = ["default", "walking", "running", "sitting", "t_pose", "debug_all"]
    pose_name = "default"
    
    if p_choice.isdigit() and 0 <= int(p_choice) < len(pose_map):
        pose_name = pose_map[int(p_choice)]
    elif p_choice:
        pose_name = p_choice
        
    # 3. Confirm
    print(f"\nProcessing {len(selected_files)} file(s) with pose '{pose_name}'...")
    
    matcher = ColorMatcher(mode="all")
    
    for idx, fpath in enumerate(selected_files):
        print(f"[{idx+1}/{len(selected_files)}] processing: {fpath}...")
        process_skin(fpath, None, "auto", pose_name, False, "all", matcher, {})
        
    print("Done!")

def main():
    parser = argparse.ArgumentParser(description="Convert Minecraft skins to Litematic statues.")
    parser.add_argument("-i", "--input", help="Path to skin file or directory")
    parser.add_argument("-o", "--output", help="Output directory or file")
    parser.add_argument("-p", "--pose", default="default", help="Pose name or path to json")
    parser.add_argument("-l", "--list-poses", action="store_true", help="List all available poses")
    parser.add_argument("--debug", action="store_true", help="Generate debug gallery (alias for --pose debug_all)")
    parser.add_argument("--solid", action="store_true", help="Disable hollow optimization")
    parser.add_argument("--palette", default="all", choices=["all", "wool", "concrete", "terracotta"], help="Block palette")
    parser.add_argument("-m", "--model", default="auto", choices=["auto", "classic", "slim"], help="Model type")
    
    if len(sys.argv) == 1:
        # No args -> Interactive
        interactive_mode()
        return

    args = parser.parse_args()
    
    if args.list_poses:
        print("Available Poses:")
        for p in sorted(PoseApplicator.POSES.keys()):
            print(f" - {p}")
        return

    input_path = args.input
    if not input_path:
        print("Error: Input path required (use -i or interactive mode).")
        return

    files_to_process = []
    if os.path.isfile(input_path):
        files_to_process.append(input_path)
    elif os.path.isdir(input_path):
        # Scan dir
        # Only pngs
        files_to_process = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith('.png')]
        print(f"Found {len(files_to_process)} skins in directory.")
        
    if not files_to_process:
        print("No valid input files found.")
        return
        
    # Setup Global components
    matcher = ColorMatcher(mode=args.palette)
    pose = "debug_all" if args.debug else args.pose
    
    # Process
    success_count = 0
    for idx, fpath in enumerate(files_to_process):
        print(f"[{idx+1}/{len(files_to_process)}] Processing {os.path.basename(fpath)}...")
        if process_skin(fpath, args.output, args.model, pose, args.solid, args.palette, matcher, {}):
            success_count += 1
            
    print(f"\nBatch Complete. {success_count}/{len(files_to_process)} successful.")

if __name__ == "__main__":
    main()
