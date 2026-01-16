from typing import List, Tuple, Dict, Set, Optional
from PIL import Image
import numpy as np

from .primitives import BoxPart, PixelBlock, Node

class Rasterizer:
    @staticmethod
    def rasterize(parts: List[BoxPart], skin: Image.Image, solid: bool = False) -> List[PixelBlock]:
        """
        Generates a list of colored blocks using Vectorized Inverse Mapping.
        Strategy:
        1. Determine Global AABB.
        2. Generate 3D Grid of Candidate Voxels.
        3. For each part, Inverse Transform Grid -> Local.
        4. Mask points strictly inside the part box.
        5. Map Local Points -> UV -> Color.
        6. Apply Painters Algorithm (Overlays overwrite).
        7. Apply Hollow Optimization (Erosion) if needed.
        """
        # Ensure skin is RGBA and numpy array
        if skin.mode != "RGBA":
            skin = skin.convert("RGBA")
        
        # skin_data: (Height, Width, 4)
        skin_data = np.array(skin)
        skin_h, skin_w, _ = skin_data.shape
        
        # 1. Calculate Global AABB
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        
        # Sort candidates to ensure overlays overwrite
        # Actually logic is: Iterate all parts. 
        # If multiple parts claim a voxel, which one wins?
        # Overlays should win over Body.
        # Small parts inside big parts? (e.g. Arms inside Body?)
        # Standard: Overlays (secondary layer) > Body (primary).
        # We process in order: Base, then Overlay. Later overwrites earlier.
        sorted_parts = sorted(parts, key=lambda p: p.is_overlay)

        for part in parts:
            (p_min_x, p_min_y, p_min_z), (p_max_x, p_max_y, p_max_z) = part.get_aabb_world()
            min_x = min(min_x, p_min_x)
            min_y = min(min_y, p_min_y)
            min_z = min(min_z, p_min_z)
            max_x = max(max_x, p_max_x)
            max_y = max(max_y, p_max_y)
            max_z = max(max_z, p_max_z)

        # Padding
        pad = 1
        ix_min, iy_min, iz_min = int(min_x), int(min_y), int(min_z)
        ix_max, iy_max, iz_max = int(max_x) + 1, int(max_y) + 1, int(max_z) + 1
        
        # 2. Generate Grid
        # Meshgrid of World Coordinates (Centers = +0.5)
        # We work with Integer coordinates for the grid, add 0.5 for sampling
        
        x_range = np.arange(ix_min, ix_max + 1)
        y_range = np.arange(iy_min, iy_max + 1)
        z_range = np.arange(iz_min, iz_max + 1)
        
        # Create full 3D grid: (Z, Y, X) order in indexing usually, but we want (Nx3)
        # indexing='ij' means dimensions are (X, Y, Z)
        grid_x, grid_y, grid_z = np.meshgrid(x_range, y_range, z_range, indexing='ij')
        
        # Flatten
        flat_x = grid_x.ravel()
        flat_y = grid_y.ravel()
        flat_z = grid_z.ravel()
        
        total_voxels = flat_x.size
        # World Sampling Points (Center of voxel)
        world_points = np.stack((flat_x + 0.5, flat_y + 0.5, flat_z + 0.5, np.ones_like(flat_x)), axis=1)
        
        # Buffer to store result: (N, 4) - RGBA. Init with 0.
        # We can map back to 3D array for Hollow check later.
        # Dimensions of grid:
        dim_x = x_range.size
        dim_y = y_range.size
        dim_z = z_range.size
        
        volume_colors = np.zeros((dim_x*dim_y*dim_z, 4), dtype=np.uint8)
        
        for part in sorted_parts:
            # Get Matrix
            mat_tuple = part.get_world_matrix()
            mat = np.array(mat_tuple).reshape(4, 4)
            
            # Invert Matrix for World -> Local
            try:
                inv_mat = np.linalg.inv(mat)
            except np.linalg.LinAlgError:
                continue
                
            # Transform All Points to Local
            # P_local = P_world @ InvT
            local_points = world_points @ inv_mat.T
            
            # Extract lx, ly, lz
            lx = local_points[:, 0]
            ly = local_points[:, 1]
            lz = local_points[:, 2]
            
            # Check Bounds (Strictly inside [0, w) )
            w, h, d = part.size
            epsilon = 0.001
            # Note: 0 <= lx < w. 
            mask = (lx >= -epsilon) & (lx < w + epsilon) & \
                   (ly >= -epsilon) & (ly < h + epsilon) & \
                   (lz >= -epsilon) & (lz < d + epsilon)
                   
            if not np.any(mask):
                continue
                
            # Filter valid points
            valid_indices = np.where(mask)[0]
            vlx = lx[valid_indices]
            vly = ly[valid_indices]
            vlz = lz[valid_indices]
            
            # Map to UV
            # Vectorized "get_texture_coord"
            
            # Determine distances to faces
            # faces: left(x=0), right(x=w), bottom(y=0), top(y=h), front(z=0), back(z=d)
            dist_left = np.abs(vlx)
            dist_right = np.abs(w - vlx)
            dist_bot = np.abs(vly)
            dist_top = np.abs(h - vly)
            dist_front = np.abs(vlz) # Correct? Front assumed Z=0 in prvious logic
            dist_back = np.abs(d - vlz)
            
            # We want "Nearest Face".
            # Stack distances: (M, 6)
            dists = np.stack([dist_left, dist_right, dist_bot, dist_top, dist_front, dist_back], axis=1)
            min_dists = np.min(dists, axis=1)
            
            # Argmin to find which face
            # 0: left, 1: right, 2: bot, 3: top, 4: front, 5: back
            face_indices = np.argmin(dists, axis=1)
            
            # We also need UVs. Init arrays.
            # We'll compute u_local, v_local for valid points.
            u_final = np.zeros_like(vlx, dtype=np.int32)
            v_final = np.zeros_like(vlx, dtype=np.int32)
            valid_uv_mask = np.zeros_like(vlx, dtype=bool)
            
            # Helper to apply logic per face type
            def map_face(idx, face_key, u_expr, v_expr, cond_mask_subset):
                # idx: face index (0-5)
                # face_key: 'top', 'left' etc.
                # u_expr: lambda lx, ly, lz
                # v_expr: lambda lx, ly, lz
                # cond_mask_subset: boolean mask of checks that matched this face
                
                if face_key not in part.uv_map:
                    return
                
                # Get UV rect
                base_u, base_v, fw, fh = part.uv_map[face_key]
                
                # Get coordinates for these points
                # Note: These are float local coords
                # We need to map them to integer texture offsets
                # Usually floor() or round()?
                # Since we sampled center +0.5 and transformed, we are at some float position.
                # Simply clamping/floor is standard.
                
                # Example: lx=0.5 -> pixel 0.
                
                f_lx = vlx[cond_mask_subset]
                f_ly = vly[cond_mask_subset]
                f_lz = vlz[cond_mask_subset]
                
                u_off = u_expr(f_lx, f_ly, f_lz)
                v_off = v_expr(f_lx, f_ly, f_lz)
                
                # Floor and Clamp
                # E.g. top face is WxD. u_off should be in [0, w).
                # Due to projection, it might be slightly off.
                
                iu_off = np.floor(u_off).astype(np.int32)
                iv_off = np.floor(v_off).astype(np.int32)
                
                # Verify bounds of texture rect
                # This is important. If we project a point deep inside the box to the surface,
                # it maps to valid UV.
                
                # Check constraints: 0 <= iu < fw
                valid_proj = (iu_off >= 0) & (iu_off < fw) & (iv_off >= 0) & (iv_off < fh)
                
                # Write results
                # We need indices in 'face_indices' array
                # cond_mask_subset is boolean mask relative to 'valid_indices'
                
                # Actually, simpler: 
                # global indices for this part calc: valid_indices
                # subset: valid_indices[cond_mask_subset]
                
                # Wait, 'cond_mask_subset' is size sum(cond).
                
                # Let's write to temp arrays u_final, v_final using boolean indexing on them?
                # Yes.
                
                np.place(u_final, cond_mask_subset, base_u + iu_off[valid_proj]) # This relies on alignment... risky
                # Safer:
                
                # Indices where this face matched AND projection valid
                # Relative to `valid_indices` array
                
                # First, fill temp arrays of matching size
                temp_u = np.zeros(np.sum(cond_mask_subset), dtype=np.int32)
                temp_v = np.zeros(np.sum(cond_mask_subset), dtype=np.int32)
                temp_valid = np.zeros(np.sum(cond_mask_subset), dtype=bool)
                
                temp_u[valid_proj] = base_u + iu_off[valid_proj]
                temp_v[valid_proj] = base_v + iv_off[valid_proj]
                temp_valid[valid_proj] = True
                
                # Transfer to main arrays
                # u_final[cond_mask_subset] = temp_u
                # We can do this if shapes match.
                
                # Actually, just looping is easier or boolean indexing.
                u_final[cond_mask_subset] = temp_u
                v_final[cond_mask_subset] = temp_v
                valid_uv_mask[cond_mask_subset] = temp_valid

            # Define expressions (matching previous logic)
            # Top: x=x, z=y (UV space). Map u=lx, v=lz
            map_face(3, 'top', lambda x,y,z: x, lambda x,y,z: z, face_indices == 3)
            
            # Bottom: u=lx, v=lz
            map_face(2, 'bottom', lambda x,y,z: x, lambda x,y,z: z, face_indices == 2)
            
            # Front: u=lx, v=h-ly-1
            # Note: h is part height.
            map_face(4, 'front', lambda x,y,z: x, lambda x,y,z: h - y, face_indices == 4)
            # -1 or not? floor(h - 0.5) = h-1. Correct. 
            
            # Back: u=lx, v=h-ly
            map_face(5, 'back', lambda x,y,z: x, lambda x,y,z: h - y, face_indices == 5)
            
            # Left: u=lz, v=h-ly
            map_face(0, 'left', lambda x,y,z: z, lambda x,y,z: h - y, face_indices == 0)
            
            # Right: u=lz, v=h-ly
            map_face(1, 'right', lambda x,y,z: z, lambda x,y,z: h - y, face_indices == 1)
            
            # Get Colors
            # Only where valid_uv_mask is True
            final_valid_indices = valid_indices[valid_uv_mask]
            
            if final_valid_indices.size > 0:
                # Get UVs
                us = u_final[valid_uv_mask]
                vs = v_final[valid_uv_mask]
                
                # Sample Skin
                # skin_data is [Y, X]
                # Clip to safe bounds
                us = np.clip(us, 0, skin_w - 1)
                vs = np.clip(vs, 0, skin_h - 1)
                
                colors = skin_data[vs, us] # (M, 4)
                
                # Alpha Threshold
                alpha_mask = colors[:, 3] > 0
                
                final_cols = colors[alpha_mask]
                final_grid_indices = final_valid_indices[alpha_mask]
                
                # Update Volume Buffer
                if final_grid_indices.size > 0:
                    volume_colors[final_grid_indices] = final_cols
                    
        # 3. Optimizations (Solid/Hollow)
        # Reshape volume to 3D
        volume_3d = volume_colors.reshape(dim_x, dim_y, dim_z, 4)
        
        # Identify non-empty
        # Using alpha > 0
        has_block = volume_3d[:, :, :, 3] > 0
        
        # If Hollow requested (not solid)
        if not solid:
            # Erode: Keep only if surface
            # Surface = Has at least one empty neighbor (6-neighbors)
            # Pad to handle edges easily
            padded = np.pad(has_block, 1, mode='constant', constant_values=0)
            
            # Neighbors
            n_x1 = padded[2:, 1:-1, 1:-1]
            n_x2 = padded[:-2, 1:-1, 1:-1]
            n_y1 = padded[1:-1, 2:, 1:-1]
            n_y2 = padded[1:-1, :-2, 1:-1]
            n_z1 = padded[1:-1, 1:-1, 2:]
            n_z2 = padded[1:-1, 1:-1, :-2]
            
            # Internal = All 6 neighbors are present
            internal = n_x1 & n_x2 & n_y1 & n_y2 & n_z1 & n_z2
            
            # We remove internals
            # Keep = has_block AND NOT internal
            keep_mask = has_block & (~internal)
        else:
            keep_mask = has_block
            
        # Extract Final List
        # Get coordinates where keep_mask is True
        # Note: These are indices into x_range, etc.
        valid_z, valid_y, valid_x = np.where(keep_mask) # Note indices are from indexing='ij' -> X,Y,Z?
        # Checked meshgrid earlier: indexing='ij' -> dim_x, dim_y, dim_z.
        # So mask indices are ix, iy, iz.
        # But wait, np.where returns in tuple(dim0_indices, dim1_indices...)
        # dim0 is X, dim1 is Y, dim2 is Z.
        valid_ix, valid_iy, valid_iz = np.where(keep_mask)
        
        # Map to World Coordinates
        wx = x_range[valid_ix]
        wy = y_range[valid_iy]
        wz = z_range[valid_iz]
        
        # Get Colors
        final_colors = volume_3d[valid_ix, valid_iy, valid_iz]
        
        # Build List
        # Zip and Create
        # Vectorized list creation?
        # Standard Python list comp is fast enough for <100k items
        
        # Ensure native types
        return [
            PixelBlock(int(wx[i]), int(wy[i]), int(wz[i]), int(r), int(g), int(b), int(a))
            for i, (r, g, b, a) in enumerate(final_colors)
        ]
