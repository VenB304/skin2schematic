from dataclasses import dataclass
from typing import List, Tuple, Dict, Iterator
from PIL import Image

@dataclass
class PixelBlock:
    x: int
    y: int
    z: int
    r: int
    g: int
    b: int
    a: int
    is_overlay: bool = False

class SkinGeometry:
    # Part Definition: (u, v, w, h, d, world_x, world_y, world_z, is_overlay)
    # world_x,y,z are RELATIVE to the part's origin in the statue
    
    # Statue Coordinate System (1:1 blocks):
    # Width (X): 16 blocks (Arm 4 + Body 8 + Arm 4)
    # Height (Y): 32 blocks (Leg 12 + Body 12 + Head 8)
    # Depth (Z): 8 blocks (Head 8, Body 4)
    
    # Global Offsets for parts (Base point):
    # Right Arm: X=0
    # Right Leg: X=4 (Wait, Steve Right Leg is usually X=4..8 in logic? Let's verify)
    # If Visual Right (Viewer's Left) is X=0..4.
    # Steve's Right Arm is on HIS Right.
    # If he faces North (-Z), his Right is East (+X).
    # So His Right Arm is X=12..16?
    # Let's standardize:
    # X axis runs Left -> Right (Viewer perspective from front).
    # Left Arm (Viewer Left) -> X=0..4.
    # Left Leg -> X=4..8.
    # Right Leg -> X=8..12.
    # Right Arm -> X=12..16.
    # (Note: Left/Right naming is from Statue's perspective usually)
    # Statue's Right Arm (Viewer Left) = X=0.
    # This matches "Starboard/Port" confusion.
    # Let's stick to "Starboard" (Right side of ship).
    # If facing North (-Z), Starboard is East (+X).
    # So Statue Right = +X.
    # So Right Arm is at X=12..16. Right Leg X=8..12.
    # Left Leg X=4..8. Left Arm X=0..4.
    
    # Part Origins (Base Layer):
    # Head: X=4, Y=24, Z=0. (8x8x8). Center X=8.
    # Body: X=4, Y=12, Z=2. (8x12x4). Center X=8.
    # Right Arm: X=12, Y=12, Z=2. (4x12x4).
    # Left Arm: X=0, Y=12, Z=2. (4x12x4).
    # Right Leg: X=8, Y=0, Z=2. (4x12x4).
    # Left Leg: X=4, Y=0, Z=2. (4x12x4).
    
    # Note: Slim model modifies arm widths to 3.
    # Right Arm (Slim): X=12, Y=12, Z=2. (Width 3 -> X=12..15).
    # Left Arm (Slim): X=1, Y=12, Z=2. (Width 3 -> X=1..4). (Shifted to touch body at X=4).
    
    @staticmethod
    def generate_blocks(skin: Image.Image, model: str = "classic") -> List[PixelBlock]:
        blocks = []
        
        # Helper to process a box
        def process_box(name, u, v, w, h, d, ox, oy, oz, overlay=False):
            # Iterate faces
            # Texture Layout Standard:
            # Top: (u+d, v, w, d)
            # Bottom: (u+d+w, v, w, d)
            # Right: (u, v+d, d, h)
            # Front: (u+d, v+d, w, h)
            # Left: (u+d+w, v+d, d, h)
            # Back: (u+d+w+d, v+d, w, h)
            
            # Note: "Right" in texture map usually means 'Outer Right' of the limb?
            # For Right Arm: Right Face is the outer face.
            # For Left Arm: Right Face is the inner face?
            # We need to map faces to 3D normals correctly.
            
            # Map faces to (local_x range, local_y range, local_z range) relative to ox,oy,oz.
            # Local Box: x in [0, w), y in [0, h), z in [0, d)
            # Y acts normally (0 is bottom). Texture Y is top-down.
            
            # Top Face (Y=max)
            # Texture region: x: u+d .. u+d+w, y: v .. v+d
            # Maps to: x: 0..w, z: 0..d
            for tx in range(w):
                for tz in range(d):
                    color = skin.getpixel((u + d + tx, v + tz))
                    if color[3] > 0:
                        # 3D coords. Top face is at y=h (or h-1).
                        # Texture Z (tz) 0 is 'Back'? No, usually Top texture implies Z runs 0..d.
                        # We map tx->x, tz->z.
                        # Overlay shift: If overlay, we push OUTWARDS 1 block.
                        # Since we are creating a shell, the overlay blocks are valid blocks at (ox -1 ..)
                        # But wait, the USER wants "1-block-thick shells". 
                        # This means we simply render them at their expanded magnitude.
                        # Base layer: Head is 8x8. Overlay layer: Head is 10x10.
                        # We just treat the overlay as a larger box.
                        # Is the texture mapping stretch or 1:1?
                        # Minecraft renders overlays 1:1 pixels but 'floating' slightly.
                        # Since we must use blocks, we effectively SCALE the overlay box to fit the pixels?
                        # No, the overlay texture is SAME resolution (8x8 face) usually.
                        # So we have 8x8 pixels for a 10x10 face? No.
                        # Overlay textures match the base part size (e.g. Head Overlay Front is 8x8 pixels).
                        # But we want to wrap it around.
                        # If we place it at r+1, we have a 10x10 face space to fill with 8x8 pixels.
                        # This implies GAPS or STRETCHING.
                        # "Sit correctly offset from base layers"
                        # If 1 pixel = 1 block.
                        # Base Head = 8 blocks wide.
                        # Overlay Head = 10 blocks wide (wrapping around).
                        # But the texture only provides 8 blocks of data!
                        # We can't stretch 8 blocks to 10.
                        # SOLUTION: floated blocks? 'No floating offsets' allowed by standard blocks.
                        # Maybe the user implies the overlay should REPLACE the base if opaque?
                        # OR: The statue is hollow?
                        # OR: "Overlay" simply means we place the overlay pixel INSTEAD of the base pixel if present?
                        # NO, "Include base skin layer AND all outer/overlay layers... 1-block-thick shells".
                        # This implies separation.
                        # If I build a valid MC statue, the 'Helmet' is usually a separate layer.
                        # If 1px = 1block.
                        # We can place the helmet at the SAME coordinates but maybe slightly offset? Impossible with blocks.
                        # We MUST shift by at least 1 block.
                        # If we shift by 1 block, the box becomes bigger.
                        # If the texture is 8x8, we can center it on the 10x10 face?
                        # i.e. leave a 1-block border of air?
                        # This works!
                        # So, Head Overlay (HAT):
                        # Box Size 10x10x10.
                        # Front Face is 10x10.
                        # We have 8x8 pixels.
                        # We place them at x=1..9, y=1..9.
                        # This preserves 1:1 pixel scale and creates the shell effect!
                        
                        dx = 0
                        dy = 0
                        dz = 0
                        
                        if overlay:
                            # Shift local coords by +1 to center within the +2 sized box
                            # And the box itself starts at -1 relative to base
                            # So Top Face is at y=h (base h is top of base). Overlay top is at h+1.
                            # So we place at y = h+1.
                            # x = tx + 1.
                            # z = tz + 1.
                            pass
                            
                        # Actual Logic:
                        # Top Face:
                        bx = tx
                        by = h if overlay else h - 1 # Top of base is h-1. Overlay top is just above.
                        bz = tz
                        
                        # Fix Overlay Spacing
                        if overlay:
                            # Shift range: Base 0..w-1. Overlay needs to be around it.
                            # So Overlay X range is -1 .. w.
                            # But we have pixels 0..w-1.
                            # We place them at 0..w-1 but shifted?
                            # No, we assume the texture represents the 'surface'.
                            # If we just place the overlay pixels at r=1 (distance 1 from base),
                            # relative to the base surface.
                            # Top Face Overlay: Placed at Y = h. X match base, Z match base.
                            # This puts the 'hat' directly on top of the 'head'.
                            # What about side overhangs?
                            # Hat usually covers sides too.
                            # If we only extrude faces, we get a disjointed shell (edges missing).
                            # A 8x8 top face, 8x8 front face.
                            # If we place Top at Y=h, X=0..8, Z=0..8.
                            # And Front at Z=-1, X=0..8, Y=0..8.
                            # They don't touch at the corner! (Corner is Y=h, Z=-1).
                            # The corner pixel is missing.
                            # But user said "1:1 scale".
                            # It is acceptable to have disjoint floating plates for the overlay if that ensures 1:1.
                            # Or we just accept it. "1-block-thick shells".
                            # I will implement the "Face Extrusion" method.
                            # Top Face -> Y+1
                            # Bottom Face -> Y-1
                            # Right Face -> X+1 (Right means local width max?) -> Local X = -1?
                            # Let's verify 'Right'.
                            # Texture Right Face: x=u..u+d.
                             
                            pass
                        
                        # Let's map directly to final Global Coords then shift.
                        # Local -> Global
                        # Base X (0..w) -> +x direction
                        # Base Y (0..h) -> +y direction
                        # Base Z (0..d) -> +z direction
                        
                        # Face Mappings (Standard "Folded" Box):
                        # Top (Y max): x=tx, z=tz. y = h-1 (base) or h (overlay).
                        # Bottom (Y min): x=tx + w, z=tz ?? No.
                        # Standard Box Map:
                        # Top: x=tx, z=tz. (Matches x,z plane)
                        # Bottom: x=tx + w? No texture is (u+d+w, v). x=tx, z=tz.
                        # Wait, Top/Bottom usually flip in UV map.
                        # Top: (x, z). Bottom: (x, z).
                        # Let's assume standard intuitive mapping:
                        # Top (Head): Header points 'up' in texture? No.
                        # (8,0) is Top-Left of Top Face.
                        # Maps to Statue Left-Back?
                        # Let's assume (0,0) of face maps to (0,0) of local face rect.
                        
                        # Top Face: Y = h (overlay) / h-1 (base). X = tx, Z = tz.
                        final_x = ox + tx
                        final_y = oy + (h if overlay else h-1)
                        final_z = oz + tz
                        
                        blocks.append(PixelBlock(final_x, final_y, final_z, *color))
            
            # Helper for Faces
            def add_face(face_u, face_v, fw, fh, map_cb):
                 for fx in range(fw):
                    for fy in range(fh):
                        c = skin.getpixel((face_u + fx, face_v + fy))
                        if c[3] > 0:
                            lx, ly, lz = map_cb(fx, fy)
                            blocks.append(PixelBlock(ox + lx, oy + ly, oz + lz, *c, is_overlay=overlay))

            # Faces definitions for a box (u, v, w, h, d)
            # Top (u+d, v, w, d)
            add_face(u + d, v, w, d, lambda fx, fy: (fx, h if overlay else h-1, fy))
            
            # Bottom (u+d+w, v, w, d) -> Y=-1 if overlay
            add_face(u + d + w, v, w, d, lambda fx, fy: (fx, -1 if overlay else 0, fy))
            
            # Right (u, v+d, d, h) -> X=-1 if overlay? (Assuming Right is 'Left' in standard view? no)
            # Standard View: Right is the Left side of the unfolding.
            # Local X=0 is 'Right' side?
            # Let's defined Local Axes: X goes right, Y goes up, Z goes back.
            # 'Right' Face in Texture (Outer Right Arm) -> Should map to X=w (overlay) or w-1 (base).
            # Wait, Right Arm texture 'Right' is the OUTER face.
            # If Right Arm is at X=12..16. Outer face is X=16.
            # So Right Face -> X local max.
            add_face(u, v + d, d, h, lambda fx, fy: (w if overlay else w-1, h - 1 - fy, fx)) 
            # Note: y maps inverse (texture down = y down). z maps to fx (face width is Depth)
            
            # Front (u+d, v+d, w, h) -> Z=0 (base) or -1 (overlay)
            add_face(u + d, v + d, w, h, lambda fx, fy: (fx, h - 1 - fy, -1 if overlay else 0))
            
            # Left (u+d+w, v+d, d, h) -> X=-1 (overlay) or 0 (base)?
            # If Right was Max X, Left is Min X (X=0).
            add_face(u + d + w, v + d, d, h, lambda fx, fy: (-1 if overlay else 0, h - 1 - fy, fx))
            
            # Back (u+d+w+d, v+d, w, h) -> Z=d (overlay) or d-1 (base)
            add_face(u + d + w + d, v + d, w, h, lambda fx, fy: (fx, h - 1 - fy, d if overlay else d-1))

        # === Define Parts ===
        # Classic Model
        # Right Arm (Viewer Left, Statue X=0 or 12? We decided Statue Right=X=12. Viewer Left=X=0)
        # So "Right Arm" in Mojang terms is the arm on the right of the character.
        # This corresponds to X=12 in our "Starboard" logic.
        
        # HEAD
        # Base: (0, 0, 8, 8, 8) -> Pose X=4, Y=24, Z=0
        process_box("Head", 0, 0, 8, 8, 8, 4, 24, 0)
        # Overlay (Hat): (32, 0, 8, 8, 8)
        process_box("Hat", 32, 0, 8, 8, 8, 4, 24, 0, overlay=True)

        # BODY
        # Base: (16, 16, 8, 12, 4) -> Pose X=4, Y=12, Z=2
        process_box("Body", 16, 16, 8, 12, 4, 4, 12, 2)
        # Overlay (Jacket): (16, 32, 8, 12, 4)
        process_box("Jacket", 16, 32, 8, 12, 4, 4, 12, 2, overlay=True)

        # ARMS & LEGS
        if model == "slim":
            arm_w = 3
            # Right Arm (Texture 44-46 is front)
            # Base: (40, 16, 3, 12, 4) -> Pose X=12, Y=12, Z=2
            process_box("RightArm", 40, 16, 3, 12, 4, 12, 12, 2)
            # Overlay: (40, 32, 3, 12, 4)
            process_box("RightSleeve", 40, 32, 3, 12, 4, 12, 12, 2, overlay=True)
            
            # Left Arm
            # Base: (32, 48, 3, 12, 4) -> Pose X=1, Y=12, Z=2 (Touching Body at 4. 1..4)
            process_box("LeftArm", 32, 48, 3, 12, 4, 1, 12, 2)
            # Overlay: (48, 48, 3, 12, 4)
            process_box("LeftSleeve", 48, 48, 3, 12, 4, 1, 12, 2, overlay=True)
        else:
            arm_w = 4
            # Right Arm
            # Base: (40, 16, 4, 12, 4) -> Pose X=12, Y=12, Z=2
            process_box("RightArm", 40, 16, 4, 12, 4, 12, 12, 2)
            # Overlay: (40, 32, 4, 12, 4)
            process_box("RightSleeve", 40, 32, 4, 12, 4, 12, 12, 2, overlay=True)
            
            # Left Arm
            # Base: (32, 48, 4, 12, 4) -> Pose X=0, Y=12, Z=2
            process_box("LeftArm", 32, 48, 4, 12, 4, 0, 12, 2)
            # Overlay: (48, 48, 4, 12, 4)
            process_box("LeftSleeve", 48, 48, 4, 12, 4, 0, 12, 2, overlay=True)

        # LEGS (Same for both)
        # Right Leg
        # Base: (0, 16, 4, 12, 4) -> Pose X=8, Y=0, Z=2 (Statue Right Leg)
        process_box("RightLeg", 0, 16, 4, 12, 4, 8, 0, 2)
        # Overlay: (0, 32, 4, 12, 4)
        process_box("RightPants", 0, 32, 4, 12, 4, 8, 0, 2, overlay=True)
        
        # Left Leg
        # Base: (16, 48, 4, 12, 4) -> Pose X=4, Y=0, Z=2
        process_box("LeftLeg", 16, 48, 4, 12, 4, 4, 0, 2)
        # Overlay: (0, 48, 4, 12, 4)
        process_box("LeftPants", 0, 48, 4, 12, 4, 4, 0, 2, overlay=True)

        return blocks
