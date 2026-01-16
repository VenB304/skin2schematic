import numpy as np
from typing import List, Tuple, Dict, Optional
from PIL import Image

class MacroVoxelizer:
    SCALE_FACTOR = 3

    # Standard offsets for T-Pose (Classic Model)
    # These are in "Pixel Units" before scaling.
    # Center of gravity/pivot is usually roughly consistent.
    # We'll use a standard layout where:
    # Head: 0-8 x, 0-8 y, 0-8 z
    # Body: 4-12 x, ...
    
    # Actually, let's map standard "Skin Parts" to "World Pixel Origins".
    # Assuming "T-Pose".
    # Head (8x8x8): Centered at 0, 24, 0 (Bottom center).
    # Bounds: [-4, 4] X, [24, 32] Y, [-4, 4] Z.
    
    # Body (8x12x4): Centered at 0, 18, 0 (Center).
    # Bounds: [-4, 4] X, [12, 24] Y, [-2, 2] Z.
    
    # Right Arm (4x12x4): Right side of body.
    # Bounds: [4, 8] X, [12, 24] Y, [-2, 2] Z.
    
    # Left Arm (4x12x4): Left side.
    # Bounds: [-8, -4] X, [12, 24] Y, [-2, 2] Z.
    
    # Right Leg (4x12x4):
    # Bounds: [0, 4] X, [0, 12] Y, [-2, 2] Z.
    
    # Left Leg (4x12x4):
    # Bounds: [-4, 0] X, [0, 12] Y, [-2, 2] Z.
    
    PARTS = {
        "Head": {
            "uv": (0, 0), "size": (8, 8, 8), 
            "origin": (-4, 24, -4), # Bottom-Left-Back corner in World Pixel Space
            "faces": {
                "top": {"uv": (8, 0), "size": (8, 8), "axis": "xz", "y_off": 8},
                "bottom": {"uv": (16, 0), "size": (8, 8), "axis": "xz", "y_off": 0},
                "right": {"uv": (0, 8), "size": (8, 8), "axis": "yz", "x_off": 8}, # Outer Right? No, Skin: Right=0,8.
                "front": {"uv": (8, 8), "size": (8, 8), "axis": "xy", "z_off": 0}, # Front is Z-? Z+? 
                # Standard Skin Map: 
                # Top(8,0), Bot(16,0).
                # Right(0,8), Front(8,8), Left(16,8), Back(24,8).
                # Face mapping requires care with directions.
                # Assuming Standard MC Coords: +Y Up, +X Left?.
                # Let's assume +Z is Front.
                # Front face is at Z (max).
                # Back face is at Z (min).
                # Right face is at X (max) or (min)? Right Arm is +X.
                # So Right Face of Head is +X?
                # Actually, MC Texture "Right" usually means "Right side of the character" (User's Right).
                # Which is -X in standard rig?
                # Let's stick to the visual map:
                # [Right][Front][Left][Back]
                # Right is usually Inner or Outer?
                # "Right" on texture is the Right cheek.
                # In T-Pose, Right Arm is at X>0.
                # So Right Cheek is X>0.
                # Left Cheek is X<0.
                
                # Correction:
                # Steve looks at -Z? Or +Z?
                # Standard convention: +Z South.
                # Let's align with the previous code if possible or just be consistent.
                # Previous code used: "front": (u+d, v+d, w, h). 
                # And generated boxes.
                
                # I will define faces with their plane normal/offset.
                # UVs are standard 64x64 or 64x32.
                # Top: (8,0, 8,8).
                # Bottom: (16,0, 8,8).
                # Right: (0,8, 8,8).
                # Front: (8,8, 8,8).
                # Left: (16,8, 8,8).
                # Back: (24,8, 8,8).
            }
        },
        # Defined individually to handle overlays properly
        # Note: We treat Overlay parts as separate pass or separate logic?
        # User says: "Inner Layer Logic" vs "Outer Layer Logic".
        # We should iterate "Skin Parts" and check both Inner and Outer UVs for each pixel? 
        # Yes.
    }
    
    # We need a robust Face iterator relative to UVs for all parts.
    # PART_DEFINITIONS = (Name, Size(w,h,d), BaseUV(u,v), Origin(x,y,z), OverlayUV(u,v))
    # Using 1.8+ Skin Layout (64x64)
    DEFINITIONS = [
        # Name, (W,H,D), BaseUV, Origin (Pixel Units), OverlayUV
        ("Head", (8, 8, 8), (0, 0), (-4, 24, -4), (32, 0)),
        ("Body", (8, 12, 4), (16, 16), (-4, 12, -2), (16, 32)),
        ("RightArm", (4, 12, 4), (40, 16), (4, 12, -2), (40, 32)), # Classic 4-wide
        ("LeftArm", (4, 12, 4), (32, 48), (-8, 12, -2), (48, 48)),
        ("RightLeg", (4, 12, 4), (0, 16), (0, 0, -2), (0, 32)), 
        ("LeftLeg", (4, 12, 4), (16, 48), (-4, 0, -2), (0, 48)),
    ]
    
    # Face Offsets (U, V, W, H) relative to Base/Overlay UV
    # (Based on W,H,D of the box)
    @staticmethod
    def get_faces(w, h, d):
        return {
            "top":    (d, 0, w, d, "y_max"),    # Top Face
            "bottom": (d+w, 0, w, d, "y_min"),  # Bottom
            "right":  (0, d, d, h, "x_max"),    # Right
            "front":  (d, d, w, h, "z_min"),    # Front (or max? let's standardise later)
            "left":   (d+w, d, d, h, "x_min"),  # Left
            "back":   (d+w+d, d, w, h, "z_max") # Back
        }

    # Orientation Mapping
    # Minecraft Skins:
    # Front is usually the face.
    # In world, +Z is South, -Z is North.
    # Let's assume Front is -Z (North) or +Z (South).
    # Codebase dumper usually puts Front at +Z or similar?
    # I'll just map (x,y,z) iteratively.

    @staticmethod
    def generate(skin_img: Image.Image, scale: int = 3, solid_mode: bool = False) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns (wx, wy, wz, colors) blocks.
        """
        # Ensure RGBA
        skin_arr = np.array(skin_img.convert("RGBA"))
        h, w_img, _ = skin_arr.shape
        
        blocks_x = []
        blocks_y = []
        blocks_z = []
        blocks_c = []
        
        # Helper to add blocks
        def add(x, y, z, c):
             blocks_x.extend(x)
             blocks_y.extend(y)
             blocks_z.extend(z)
             blocks_c.extend(c)

        for name, (bw, bh, bd), (bu, bv), (ox, oy, oz), (ou, ov) in MacroVoxelizer.DEFINITIONS:
            
            faces = MacroVoxelizer.get_faces(bw, bh, bd)
            
            # Iterate Faces
            for face_name, (fu, fv, fw, fh, axis) in faces.items():
                
                # Inner Face Loop
                for u_off in range(fw):
                    for v_off in range(fh):
                        # 1. INNER PIXEL
                        u_in = bu + fu + u_off
                        v_in = bv + fv + v_off
                        
                        pixel_in = None
                        if 0 <= u_in < w_img and 0 <= v_in < h:
                             pixel = skin_arr[v_in, u_in]
                             if pixel[3] > 10: # Opaque enough
                                 pixel_in = pixel

                        # 2. OUTER PIXEL (Overlay)
                        u_out = ou + fu + u_off
                        v_out = ov + fv + v_off
                        
                        pixel_out = None
                        if 0 <= u_out < w_img and 0 <= v_out < h:
                             pixel = skin_arr[v_out, u_out]
                             if pixel[3] > 10:
                                 pixel_out = pixel
                        
                        if pixel_in is None and pixel_out is None:
                            continue

                        # Calculate "Pixel Space" coordinate (Relative to Origin ox,oy,oz)
                        # We need to map face (u,v) to volume (x,y,z)
                        # Top (d, 0, w, d): u_off maps to x, v_off maps to z (roughly)
                        # Top Face: y = bh (top). x = u_off. z = v_off.
                        # Note: Textures are often flipped or rotated.
                        # Standard Planar Mapping:
                        # Top: x=[0..w], z=[0..d].
                        # Bottom: x=[0..w], z=[0..d].
                        # Front: x=[0..w], y=[0..h].
                        
                        # Let's calculate l_x, l_y, l_z (local pixel coords)
                        l_x, l_y, l_z = 0, 0, 0
                        
                        # Mapping Logic (Simplified for readability, verify flips if needed)
                        if face_name == "top":
                             l_x = u_off
                             l_z = v_off
                             l_y = bh - 1 # Top layer
                        elif face_name == "bottom":
                             l_x = u_off
                             l_z = v_off
                             l_y = 0
                             # Typically bottom is flipped?
                             # Let's ignore complex texture flips for 'Macro' pass unless crucial.
                             # User said "Refactor base loop".
                        elif face_name == "front":
                             l_x = u_off
                             l_y = bh - 1 - v_off # v goes down
                             l_z = 0 # Front face at 0? Or bd?
                             # If Front is -Z, it's 0. If Back is +Z, it's bd.
                             # Let's assume standard order: Z=0 is Front.
                        elif face_name == "back":
                             l_x = fw - 1 - u_off # Back often flipped horizontally?
                             l_y = bh - 1 - v_off
                             l_z = bd - 1
                        elif face_name == "right":
                             l_z = u_off
                             l_y = bh - 1 - v_off
                             l_x = bw - 1 # Right side
                        elif face_name == "left":
                             l_z = fw - 1 - u_off
                             l_y = bh - 1 - v_off
                             l_x = 0
                             
                        # Absolute Pixel Pos
                        px = ox + l_x
                        py = oy + l_y
                        pz = oz + l_z
                        
                        # --- GENERATE BLOCKS ---
                        
                        # BASE WORLD COORD
                        bx = px * scale
                        by = py * scale
                        bz = pz * scale
                        
                        # 1. INNER VOXEL (Solid Cube)
                        if pixel_in is not None:
                            # Generate cube [0, scale)
                            # Vectorized add? No, small loops are fine or use repeat.
                            # Size: scale^3
                            
                            # Create grid
                            xx, yy, zz = np.indices((scale, scale, scale))
                            xx = xx.flatten() + bx
                            yy = yy.flatten() + by
                            zz = zz.flatten() + bz
                            
                            count = xx.size
                            cc = np.tile(pixel_in, (count, 1))
                            
                            add(xx, yy, zz, cc)
                            
                        # 2. OUTER VOXEL (Hollow Shell)
                        if pixel_out is not None:
                            # Shell Logic:
                            # Offset 1 block gap.
                            # Start: -2 (Gap 1, Shell 1).
                            # End: scale + 1.
                            # Range: [-2, scale + 2).
                            # Only walls.
                            
                            start = -2
                            end = scale + 2 # Exclusive
                            full_range = range(start, end)
                            
                            # Iterating simply:
                            for sx in full_range:
                                for sy in full_range:
                                    for sz in full_range:
                                        # Check if boundary (Wall)
                                        # Boundary if any coord is at start or end-1
                                        if sx == start or sx == end - 1 or \
                                           sy == start or sy == end - 1 or \
                                           sz == start or sz == end - 1:
                                           
                                           # Add Block
                                           add([bx + sx], [by + sy], [bz + sz], [pixel_out])
                        
        # Convert to arrays
        return (
            np.array(blocks_x, dtype=np.int32),
            np.array(blocks_y, dtype=np.int32),
            np.array(blocks_z, dtype=np.int32),
            np.array(blocks_c, dtype=np.uint8)
        )

