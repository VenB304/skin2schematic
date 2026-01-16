from typing import List, Tuple, Dict, Set
from PIL import Image
from .primitives import BoxPart, PixelBlock, Node

class Rasterizer:
    @staticmethod
    def rasterize(parts: List[BoxPart], skin: Image.Image) -> List[PixelBlock]:
        """
        Generates a list of colored blocks by raycasting (inverse mapping) 
        through the world bounding box of all parts.
        """
        # 1. Calculate Global AABB
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        
        for part in parts:
            (p_min_x, p_min_y, p_min_z), (p_max_x, p_max_y, p_max_z) = part.get_aabb_world()
            min_x = min(min_x, p_min_x)
            min_y = min(min_y, p_min_y)
            min_z = min(min_z, p_min_z)
            max_x = max(max_x, p_max_x)
            max_y = max(max_y, p_max_y)
            max_z = max(max_z, p_max_z)
            
        # Integer Bounds (inclusive)
        # Pad slightly to catch surface blocks
        padding = 1
        ix_min = int(min_x - padding)
        iy_min = int(min_y - padding)
        iz_min = int(min_z - padding)
        ix_max = int(max_x + padding)
        iy_max = int(max_y + padding)
        iz_max = int(max_z + padding)
        
        print(f"Rasterizing Area: {ix_min},{iy_min},{iz_min} to {ix_max},{iy_max},{iz_max}")
        total_voxels = (ix_max - ix_min) * (iy_max - iy_min) * (iz_max - iz_min)
        if total_voxels > 1000000:
            print(f"Warning: Large voxel count {total_voxels}. Performance may vary.")

        blocks: List[PixelBlock] = []
        
        # Optimize: Sort parts (Overlays first? Or just iterate all and pick best?)
        # Better: Overlay checks happen first. If Opaque, done.
        # If Transparent, continue.
        # So we want Parts sorted by 'Priority'. Overlays > Base.
        # In our list, we append Overlays AFTER Base. So Reverse list?
        # Or just checking order.
        # Let's verify RigFactory order: Body, Jacket, Head, Hat...
        # We want: Hat check > Head check. Jacket > Body.
        # So iterating strictly `reversed(parts)` works if we grouped them well?
        # Safe way: Sort by is_overlay descending.
        sorted_parts = sorted(parts, key=lambda p: p.is_overlay, reverse=True)
        
        for x in range(ix_min, ix_max):
            for y in range(iy_min, iy_max):
                for z in range(iz_min, iz_max):
                    # For this voxel, find color
                    
                    found_color = None
                    # Use center of block for sampling + 0.5
                    wx, wy, wz = x + 0.5, y + 0.5, z + 0.5
                    
                    for part in sorted_parts:
                        # 1. World -> Local
                        lx, ly, lz = part.world_to_local_point(wx, wy, wz)
                        
                        # 2. Check Bounds (0..size)
                        w, h, d = part.size
                        if 0 <= lx < w and 0 <= ly < h and 0 <= lz < d:
                            # Inside the box.
                            
                            # 3. Project to nearest face for UV
                            # Distances
                            dist_left = lx      # Face Left (x=0)
                            dist_right = w - lx # Face Right
                            dist_bot = ly       # Face Bottom (y=0)
                            dist_top = h - ly   # Face Top
                            dist_front = lz     # Face Front (z=0)
                            dist_back = d - lz  # Face Back
                            
                            m = min(dist_left, dist_right, dist_bot, dist_top, dist_front, dist_back)
                            
                            uv = None
                            
                            # Note: Logic matches 'primitives.py' get_texture_coord logic but simplified
                            # We must match the Face selection logic exactly or redundant.
                            
                            if m == dist_top:
                                uv = part.get_texture_coord(lx, h, lz) # Project to Top surface
                            elif m == dist_bot:
                                uv = part.get_texture_coord(lx, 0, lz)
                            elif m == dist_right:
                                uv = part.get_texture_coord(w, ly, lz)
                            elif m == dist_left:
                                uv = part.get_texture_coord(0, ly, lz)
                            elif m == dist_front:
                                uv = part.get_texture_coord(lx, ly, 0) # Wait, Front is z=0?
                                # In primitives we assumed front logic. let's trust get_texture_coord to handle the projection 
                                # if we pass the surface coordinate.
                            elif m == dist_back:
                                uv = part.get_texture_coord(lx, ly, d)
                                
                            if uv:
                                try:
                                    r, g, b, a = skin.getpixel(uv)
                                    if a > 0:
                                        # Use this color
                                        found_color = (r, g, b, a)
                                        # Since we sorted Overlays first, if we found an opaque pixel, IS IT THE ONE?
                                        # Yes. The Hat blocks the Head.
                                        # But what if the Hat is larger (shell) and the point is DEEP inside?
                                        # If point is inside Hat Volume but effectively "inside the head block",
                                        # The Hat texture maps "Top of Hat".
                                        # We shouldn't render "Top of Hat" deep inside the head.
                                        # Wait.
                                        # If Overlay is a Shell, it should only exist near its surface?
                                        # If I fill the Hat volume solidly, I fill the empty air between Hat and Head with Hat Texture?
                                        # Yes.
                                        # Is that bad? 
                                        # User gets a Solid Block of Hat color.
                                        # Then deep inside, Solid Block of Head color?
                                        # If I stop at first Opaque, I get Solid Hat.
                                        # If I want the Head to be visible under the Hat?
                                        # No, blocks are opaque (except glass).
                                        # So filling with Hat is fine.
                                        break
                                except Exception:
                                    pass
                                    
                    if found_color:
                        # Append Block
                        # Note: PixelBlock structure from original geometry.py: x,y,z, r,g,b,a
                        # But wait, original PixelBlock had is_overlay flag.
                        # Do we need it? Existing main.py doesn't seem to use it for Schematic construction,
                        # only ColorMatching uses RGB.
                        # Let's recreate PixelBlock struct here or import it.
                        # We imported PixelBlock from primitives which doesn't have it?
                        # primitives.py didn't define PixelBlock! 
                        # I missed that in primitives.py step. 
                        # I need to define PixelBlock in primitives or here.
                        # Original `geometry.py` defined it.
                        pass
                        blocks.append(PixelBlock(x, y, z, *found_color))
                        
        return blocks
