from typing import List
from PIL import Image
import numpy as np

from .primitives import BoxPart, PixelBlock

class SimpleVoxelizer:
    @staticmethod
    def generate(parts: List[BoxPart], skin: Image.Image, ignore_overlays: bool = False) -> List[PixelBlock]:
        """
        Generates blocks by iterating box dimensions and mapping directly to UVs.
        Assumes parts are axis-aligned (rotation is ignored).
        """
        if skin.mode != "RGBA":
            skin = skin.convert("RGBA")
        
        skin_data = np.array(skin)
        skin_h, skin_w, _ = skin_data.shape
        
        blocks = []
        
        # Sort parts: Body first, then Overlays. 
        # Overlays overwriting body is handled by order since we just append?
        # No, for a single list of blocks, we need to handle duplicates.
        # Dictionary {(x,y,z) -> block}
        
        block_map = {}
        
        # Process base parts first, then overlays
        sorted_parts = sorted(parts, key=lambda p: getattr(p, 'is_overlay', False))
        
        for part in sorted_parts:
            if ignore_overlays and getattr(part, 'is_overlay', False):
                continue
                
            # Get World Position (Translation Only)
            # We assume rotation is Identity for 'standing'
            # Node.origin is the offset. 
            # We need absolute world position.
            # Ideally "standing" pose yields correct world transforms.
            
            # Since we can't easily rely on matrix decomposition if rotation exists,
            # we will trust the user uses this validly (Standing pose).
            
            # Inspect matrix from get_world_matrix
            mat_tuple = part.get_world_matrix()
            mat = np.array(mat_tuple).reshape(4, 4)
            
            # Extract translation (Matrix is Row, Col -> [0,3])
            tx = int(mat[0, 3])
            ty = int(mat[1, 3])
            tz = int(mat[2, 3])
            
            w, h, d = part.size
            w, h, d = int(w), int(h), int(d)
            
            # Iterate Physical Bounds (Restore 10x10x10 for Hat)
            for lx in range(w):
                for ly in range(h):
                    for lz in range(d):
                        
                        # Calculate UV
                        u, v = -1, -1
                        
                        # Face logic (Simple Box mapping)
                        # Determine nearest face to handle Volume -> Surface mapping
                        dist_left = lx
                        dist_right = w - 1 - lx
                        dist_bot = ly
                        dist_top = h - 1 - ly
                        dist_front = lz
                        dist_back = d - 1 - lz
                        
                        dists = [dist_left, dist_right, dist_bot, dist_top, dist_front, dist_back]
                        face_idx = dists.index(min(dists))
                        
                        face_key = None
                        if face_idx == 0: face_key = 'left'
                        elif face_idx == 1: face_key = 'right'
                        elif face_idx == 2: face_key = 'bottom'
                        elif face_idx == 3: face_key = 'top'
                        elif face_idx == 4: face_key = 'front'
                        elif face_idx == 5: face_key = 'back'
                        
                        if face_key not in part.uv_map:
                            continue
                            
                        # Texture Face Dimensions
                        base_u, base_v, fw, fh = part.uv_map[face_key]
                        
                        # Face-Specific Dimensions on Box
                        # used for Scaling Ratio (Texture Dim / Box Dim)
                        box_fw, box_fh = 1, 1
                        u_source, v_source = 0, 0
                        
                        if face_key == 'top': # x, z
                            box_fw, box_fh = w, d
                            u_source, v_source = lx, lz
                        elif face_key == 'bottom': # x, z
                            box_fw, box_fh = w, d
                            u_source, v_source = lx, lz
                        elif face_key == 'front': # x, y
                            box_fw, box_fh = w, h
                            u_source, v_source = lx, h - 1 - ly
                        elif face_key == 'back': # x, y
                            box_fw, box_fh = w, h
                            u_source, v_source = lx, h - 1 - ly
                        elif face_key == 'left': # z, y
                            box_fw, box_fh = d, h
                            u_source, v_source = lz, h - 1 - ly
                        elif face_key == 'right': # z, y
                            box_fw, box_fh = d, h
                            u_source, v_source = lz, h - 1 - ly
                            
                        # Nearest Neighbor Scaling
                        # Map Box Coordinate (0..box_fw) to Texture Coordinate (0..fw)
                        # Avoid div by zero
                        scale_x = fw / max(1, box_fw)
                        scale_y = fh / max(1, box_fh)
                        
                        u_off = int(u_source * scale_x)
                        v_off = int(v_source * scale_y)
                        
                        # Clamp for safety (floating point jitter)
                        u_off = min(u_off, fw - 1)
                        v_off = min(v_off, fh - 1)
                        
                        u = base_u + u_off
                        v = base_v + v_off
                        
                        # Sample
                        if 0 <= u < skin_w and 0 <= v < skin_h:
                            rgba = skin_data[v, u]
                            if rgba[3] > 0: # Alpha check
                                
                                # World Coord
                                wx = tx + lx
                                wy = ty + ly
                                wz = tz + lz
                                
                                block_map[(wx, wy, wz)] = rgba
                                
        # Convert to list
        for (x, y, z), (r, g, b, a) in block_map.items():
            blocks.append(PixelBlock(x, y, z, int(r), int(g), int(b), int(a)))
            
        return blocks
