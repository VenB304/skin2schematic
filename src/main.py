import argparse
import sys
import os
import json
import glob
import multiprocessing
import numpy as np
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
from geometry.items import ItemFactory 

def process_skin_wrapper(args):
    """
    Wrapper for multiprocessing.
    args: (input_path, output_path, model, pose_name, solid, palette, cache_copy)
    Returns: (bool, cache_updates)
    """
    input_path, output_path, model, pose_name, solid, palette, cache_copy = args
    # Re-init matcher to avoid pickling large objects or sharing state issues
    matcher = ColorMatcher(mode=palette)
    return process_skin(input_path, output_path, model, pose_name, solid, palette, matcher, cache_copy)

def process_skin(input_path: str, output_path: str, model: str, pose_name: str, solid: bool, palette: str, matcher: ColorMatcher, cache: dict) -> Tuple[bool, dict]:
    """
    Process a single skin file. 
    Returns: (Success, Cache_Updates_Dict)
    """
    local_cache_updates = {}
    try:
        try:
            skin_img = SkinLoader.load_skin(input_path)
        except Exception as e:
            print(f"Error loading skin {os.path.basename(input_path)}: {e}")
            return False, {}

        detected_model = model
        if detected_model == "auto":
            detected_model = SkinLoader.detect_model(skin_img)
        
        # Determine Pose and Item
        pose_key = pose_name
        item_type = None
        item_material = None
        
        if pose_name.startswith("sword_charge"):
            pose_key = "sword_charge"
            parts = pose_name.split('_')
            # sword_charge or sword_charge_diamond
            if len(parts) > 2:
                item_material = parts[2] # diamond
            else:
                item_material = "iron" # default
            item_type = "sword"
            
        elif pose_name == "bow_aim":
            pose_key = "bow_aim"
            item_type = "bow"
            
        # Get Pose Data
        pose_data = {}
        if pose_key == "debug_all":
            pass # Handled below
        elif pose_key in PoseApplicator.POSES:
            pose_data = PoseApplicator.get_pose(pose_key)
        else:
            # Fallback for file or default
            if pose_key.endswith(".json") and os.path.exists(pose_key):
                with open(pose_key, 'r') as f:
                    pose_data = json.load(f)
            else:
                pose_data = PoseApplicator.get_standing_pose()

        # Prepare List of Poses to Render
        poses_to_render = []
        if pose_key == "debug_all":
            for name in sorted(PoseApplicator.POSES.keys()):
                p_item = None
                p_mat = None
                
                if name == "sword_charge":
                    p_item = "sword"
                    p_mat = "iron"
                elif name == "bow_aim":
                    p_item = "bow"
                
                poses_to_render.append((name, PoseApplicator.get_pose(name), p_item, p_mat))
                    
            if pose_key == "debug_all":
                for mat in ["wood", "stone", "gold", "diamond", "netherite"]:
                    name = f"sword_charge_{mat}"
                    poses_to_render.append((name, PoseApplicator.get_pose("sword_charge"), "sword", mat))
                    
        else:
             poses_to_render.append((pose_name, pose_data, item_type, item_material))

        # Setup Builder
        base_name = os.path.basename(input_path).rsplit('.', 1)[0]
        schem_name = f"Statue_{base_name}"
        if pose_name == "debug_all":
            schem_name += "_Gallery"
        
        builder = SchematicBuilder(name=schem_name)
        
        # Output Path Logic
        final_output = output_path
        if not final_output:
            output_dir = f"{base_name} output"
            os.makedirs(output_dir, exist_ok=True)
            suffix = f"_{pose_name}" if pose_name != "debug_all" else "_debug_all"
            final_output = os.path.join(output_dir, f"{base_name}{suffix}.litematic")
        elif os.path.isdir(final_output) or final_output.endswith(os.sep):
             os.makedirs(final_output, exist_ok=True)
             suffix = f"_{pose_name}" if pose_name != "debug_all" else "_debug_all"
             final_output = os.path.join(final_output, f"{base_name}{suffix}.litematic")
        
        # Pre-compute unique colors logic is now handled per-pose or global?
        # Doing it per-pose inside rasterization is more accurate for UVs but slower?
        # Rasterizer now returns colors. We handle matching below.
        
        GAP_SIZE = 5
        last_max_x = None
        total_added = 0
        
        def find_node(n, target):
            if n.name == target: return n
            for c in n.children:
                res = find_node(c, target)
                if res: return res
            return None
        
        for p_name, p_data, p_item, p_mat in poses_to_render:
            rig = RigFactory.create_rig(model_type=detected_model)
            PoseApplicator.apply_pose(rig, p_data)
            
            # Attach Items
            parts = rig.get_parts()
            if p_item == "sword":
                hand_node = find_node(rig.root, "RightArmJoint")
                if hand_node:
                    sword_parts = ItemFactory.create_sword(p_mat, hand_node)
                    parts.extend(sword_parts)
                    
            elif p_item == "bow":
                hand_node = find_node(rig.root, "RightArmJoint")
                if hand_node:
                    bow_parts = ItemFactory.create_bow(hand_node)
                    parts.extend(bow_parts)
            
            # Optimized Rasterizer call
            # Returns raw numpy arrays
            wx, wy, wz, colors = Rasterizer.rasterize(parts, skin_img, solid=solid, return_raw=True)
            
            if wx.size == 0:
                continue
                
            # Auto Grounding
            min_y = np.min(wy)
            shift_y = -min_y
            
            local_min_x = np.min(wx)
            local_max_x = np.max(wx)
            
            if last_max_x is None:
                offset_x = 0
            else:
                offset_x = last_max_x + GAP_SIZE - local_min_x
                
            last_max_x = local_max_x + offset_x
            
            # Debug Labels
            if pose_name == "debug_all":
                 front_z_local = np.min(wz)
                 sign_z = int(front_z_local - 1)
                 sign_x = int(offset_x)
                 sign_y = 0
                 
                 disp_text = p_name
                 if p_name.startswith("sword_charge_"):
                     disp_text = p_name.replace("sword_charge_", "Sword ")
                 
                 builder.add_sign(sign_x, sign_y, sign_z, text=disp_text, facing="north")

            # Match Colors (Optimized)
            # 1. Identify unique colors
            # colors shape (N, 4)
            u_colors, inverse = np.unique(colors, axis=0, return_inverse=True)
            
            u_ids = [None] * len(u_colors)
            miss_indices = []
            miss_colors = []
            
            # 2. Check Cache
            for i, c in enumerate(u_colors):
                key = tuple(c) # (r,g,b,a)
                if key in cache:
                    u_ids[i] = cache[key]
                else:
                    miss_indices.append(i)
                    miss_colors.append(c)
            
            # 3. Batch Match Misses
            if miss_colors:
                miss_arr = np.array(miss_colors, dtype=np.uint8)
                matched_ids = matcher.match_bulk(miss_arr)
                
                for idx, block_id, col in zip(miss_indices, matched_ids, miss_colors):
                    u_ids[idx] = block_id
                    # Update cache updates
                    key = tuple(col)
                    local_cache_updates[key] = block_id
                    # Also update local scope cache to avoid re-matching same color in this loop
                    cache[key] = block_id
            
            # 4. Map back to all pixels
            u_ids_arr = np.array(u_ids)
            all_ids = u_ids_arr[inverse]
            
            # 5. Bulk Add to Builder
            # Apply offsets
            final_x = wx + int(offset_x)
            final_y = wy + int(shift_y)
            final_z = wz
            
            coords = np.stack((final_x, final_y, final_z), axis=1)
            builder.add_blocks_bulk(coords, all_ids)
            total_added += len(all_ids)

        builder.save(final_output)
        return True, local_cache_updates
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        import traceback
        traceback.print_exc()
        # Return empty updates on failure
        return False, local_cache_updates

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
    print("0. standing (Default)")
    print("1. walking")
    print("2. running")
    print("3. floor_sit (sitting)")
    print("4. t_pose")
    print("5. debug_all (Gallery)")
    
    p_choice = input("Select pose (0-5) or type name: ").strip()
    pose_map = ["standing", "walking", "running", "floor_sit", "t_pose", "debug_all"]
    pose_name = "standing"
    
    if p_choice.isdigit() and 0 <= int(p_choice) < len(pose_map):
        pose_name = pose_map[int(p_choice)]
    elif p_choice:
        pose_name = p_choice
        
    # 3. Confirm
    print(f"\nProcessing {len(selected_files)} file(s) with pose '{pose_name}'...")
    
    matcher = ColorMatcher(mode="all")
    # Load Cache
    CACHE_FILE = "color_cache_v2.json"
    cache = matcher.load_cache_from_disk(CACHE_FILE)
    
    for idx, fpath in enumerate(selected_files):
        print(f"[{idx+1}/{len(selected_files)}] processing: {fpath}...")
        
        # Extract sub-cache for current mode
        # If not present, auto-create
        current_mode = "all" # Interactive mode defaults to 'all' or implied? 
        # Interactive doesn't ask for palette, defaults to "all" in code?
        # Line 296: matcher = ColorMatcher(mode="all")
        # So we use "all"
        
        mode_cache = cache.get("all", {})
        
        success, updates = process_skin(fpath, None, "auto", pose_name, False, "all", matcher, mode_cache)
        if updates:
            # Update local mode cache
            mode_cache.update(updates)
            # Ensure it's in main cache
            cache["all"] = mode_cache
            
    # Save cache
    matcher.save_cache_to_disk(CACHE_FILE, cache)
    print("Done!")

def main():
    parser = argparse.ArgumentParser(description="Convert Minecraft skins to Litematic statues.")
    parser.add_argument("-i", "--input", help="Path to skin file or directory")
    parser.add_argument("-o", "--output", help="Output directory or file")
    parser.add_argument("-p", "--pose", default="standing", help="Pose name or path to json")
    parser.add_argument("-l", "--list-poses", action="store_true", help="List all available poses")
    parser.add_argument("--debug", action="store_true", help="Generate debug gallery (alias for --pose debug_all)")
    parser.add_argument("--solid", action="store_true", help="Disable hollow optimization")
    parser.add_argument("--palette", default="all", choices=["all", "wool", "concrete", "terracotta"], help="Block palette")
    parser.add_argument("-m", "--model", default="auto", choices=["auto", "classic", "slim"], help="Model type")
    
    if len(sys.argv) == 1:
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
        files_to_process = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith('.png')]
        print(f"Found {len(files_to_process)} skins in directory.")
        
    if not files_to_process:
        print("No valid input files found.")
        return
        
    # Setup Global components
    matcher = ColorMatcher(mode=args.palette)
    pose = "debug_all" if args.debug else args.pose
    
    # Load Cache
    CACHE_FILE = "color_cache_v2.json"
    full_cache = matcher.load_cache_from_disk(CACHE_FILE)
    
    # Get relevant sub-cache
    target_palette = args.palette
    current_cache = full_cache.get(target_palette, {})
    
    # Multiprocessing
    cpu_count = multiprocessing.cpu_count()
    workers = max(1, min(cpu_count - 1, 8)) # Use up to 8 cores, leave 1 free
    
    if len(files_to_process) > 1:
        print(f"Batch processing {len(files_to_process)} skins using {workers} workers...")
        
        # Prepare Tasks
        # We pass only the relevant sub-cache to workers to keep pickling small
        tasks = [
            (f, args.output, args.model, pose, args.solid, args.palette, current_cache)
            for f in files_to_process
        ]
        
        success_count = 0
        
        # Use simple map if workers > 1
        if workers > 1:
            with multiprocessing.Pool(processes=workers) as pool:
                results = pool.map(process_skin_wrapper, tasks)
                
            for success, updates in results:
                if success: success_count += 1
                if updates: current_cache.update(updates)
        else:
            # Serial fallback
            for task in tasks:
                 s, u = process_skin_wrapper(task)
                 if s: success_count += 1
                 if u: current_cache.update(u)
    else:
        # Single file
        print(f"Processing {files_to_process[0]}...")
        success, updates = process_skin(files_to_process[0], args.output, args.model, pose, args.solid, args.palette, matcher, current_cache)
        success_count = 1 if success else 0
        if updates: current_cache.update(updates)
            
    # Save Cache
    # Merge back into full cache
    full_cache[target_palette] = current_cache
    matcher.save_cache_to_disk(CACHE_FILE, full_cache)
    print(f"\nBatch Complete. {success_count}/{len(files_to_process)} successful.")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Windows support
    main()
