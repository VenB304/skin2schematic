import math

class ColorMatcher:
    # Palette definitions (Approximate average RGB)
    def __init__(self, mode="mixed"):
        self.PALETTES = self._load_palettes()
        self.palette = {}
        if mode == "mixed":
            self.palette.update(self.PALETTES.get("concrete", {}))
            self.palette.update(self.PALETTES.get("wool", {}))
            self.palette.update(self.PALETTES.get("terracotta", {}))
        elif mode in self.PALETTES:
            self.palette = self.PALETTES[mode]
        else:
            self.palette.update(self.PALETTES.get("concrete", {}))
            self.palette.update(self.PALETTES.get("wool", {}))
            
        # Precompute RGB -> Lab for palette
        self.palette_lab = {}
        # Lists for vectorized access
        self.palette_ids_list = []
        self.palette_lab_list = []
        
        for block_id, rgb in self.palette.items():
            lab = self.rgb_to_lab(*rgb)
            self.palette_lab[block_id] = lab
            self.palette_ids_list.append(block_id)
            self.palette_lab_list.append(lab)
            
        import numpy as np
        self.palette_lab_arr = np.array(self.palette_lab_list) # (K, 3)

    def match_bulk(self, colors_rgba: "np.ndarray") -> "np.ndarray":
        """
        Vectorized color matching.
        colors_rgba: (N, 4) uint8 numpy array
        Returns: (N,) list or array of block_ids
        """
        import numpy as np
        
        # Filter transparent
        # alpha < 128 -> None
        # We handle this by returning None or "air"?
        # Usually checking alpha before calling this is better, but let's handle it.
        
        # RGB -> Lab
        # Vectorized RGB->Lab is needed.
        # Reuse local or static logic? 
        # We can just implement a fast approximate or full vector helper.
        
        r = colors_rgba[:, 0]
        g = colors_rgba[:, 1]
        b = colors_rgba[:, 2]
        a = colors_rgba[:, 3]
        
        # Vectorized RGB->Lab
        # Scale
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0
        
        # Pivot RGB
        # mask = n > 0.04045
        # ...
        # Faster to use simple lambda?
        # ((n + 0.055) / 1.055) ** 2.4
        
        def pivot_v(n):
            return np.where(n > 0.04045, ((n + 0.055) / 1.055) ** 2.4, n / 12.92)
            
        rr = pivot_v(r)
        gg = pivot_v(g)
        bb = pivot_v(b)
        
        x = rr * 0.4124 + gg * 0.3576 + bb * 0.1805
        y = rr * 0.2126 + gg * 0.7152 + bb * 0.0722
        z = rr * 0.0193 + gg * 0.1192 + bb * 0.9505
        
        # XYZ -> Lab
        def pivot_xyz_v(n):
            return np.where(n > 0.008856, n ** (1/3), (7.787 * n) + (16/116))
            
        xn, yn, zn = 0.95047, 1.00000, 1.08883
        
        fx = pivot_xyz_v(x / xn)
        fy = pivot_xyz_v(y / yn)
        fz = pivot_xyz_v(z / zn)
        
        l_val = 116 * fy - 16
        a_val = 500 * (fx - fy)
        b_val = 200 * (fy - fz)
        
        # Shape (N, 3)
        targets_lab = np.stack([l_val, a_val, b_val], axis=1)
        
        # Calculate Distances to Palette (K, 3)
        # (N, 1, 3) - (1, K, 3) -> (N, K, 3)
        # Dist sq = sum((...)**2, axis=2) -> (N, K)
        
        # Memory efficient: Process in chunks if N is huge?
        # 100k blocks * 20 palette items = 2M floats. Tiny.
        # But if palette is large... Minecraft has many blocks.
        # Current palette is small (wool/concrete ~ 32 items).
        
        diff = targets_lab[:, np.newaxis, :] - self.palette_lab_arr[np.newaxis, :, :]
        dists = np.sum(diff**2, axis=2)
        
        # Argmin
        best_indices = np.argmin(dists, axis=1)
        
        # Map to IDs
        # palette_ids_list is list of str.
        # Use np array for fast indexing?
        palette_ids_arr = np.array(self.palette_ids_list)
        results = palette_ids_arr[best_indices]
        
        # Handle alpha
        # results[a < 128] = None # Or "air"?
        # Actually Rasterizer filters alpha usually.
        
        return results

    def _load_palettes(self) -> dict:
        import os
        import json
        
        # Try finding palette.json in same dir as this file
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, 'palette.json')
        
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load palette.json: {e}")
                
        # Fallback (Hardcoded - minimal)
        return {
            "concrete": {"minecraft:white_concrete": [207, 213, 214]},
            "wool": {"minecraft:white_wool": [233, 236, 236]}
        }

    def find_nearest(self, r, g, b, a) -> str:
        if a < 128:
            return None # Air
            
        target_lab = self.rgb_to_lab(r, g, b)
            
        best_dist = float('inf')
        best_block = "minecraft:stone"
        
        for block_id, plab in self.palette_lab.items():
            # Delta E (CIE76) = Euclidean distance in Lab space
            # Slightly better than RGB distance
            dist = (target_lab[0] - plab[0])**2 + \
                   (target_lab[1] - plab[1])**2 + \
                   (target_lab[2] - plab[2])**2
                   
            if dist < best_dist:
                best_dist = dist
                best_block = block_id
                
        return best_block

    def map_unique_colors(self, image):
        """
        Optimized: identify all unique colors in the image and map them to blocks.
        Returns a dictionary: {(r, g, b, a): block_id}
        """
        # Convert to RGBA if not already
        if image.mode != "RGBA":
            image = image.convert("RGBA")
            
        # Get unique colors
        # getcolors() returns (count, pixel)
        # Max colors = 64*64 = 4096, usually much less.
        colors = image.getcolors(maxcolors=4096)
        
        mapping = {}
        if colors:
            for _, color in colors:
                # color is (r, g, b, a)
                r, g, b, a = color
                block_id = self.find_nearest(r, g, b, a)
                if block_id:
                    mapping[color] = block_id
        else:
            # Fallback for > 4096 colors (rare for skins but possible with noise)
            pixel_data = list(image.getdata())
            unique_colors = set(pixel_data)
            for color in unique_colors:
                r, g, b, a = color
                block_id = self.find_nearest(r, g, b, a)
                if block_id:
                    mapping[color] = block_id
                    
        return mapping

    def load_cache_from_disk(self, path: str) -> dict:
        import json
        import os
        
        # Determine if v2 based on filename or try load
        # We will switch to enforcing path usually passed as 'color_cache_v2.json'
        
        if not os.path.exists(path):
            return {}
            
        try:
            with open(path, 'r') as f:
                raw = json.load(f)
                
            # Check structure
            # V2: {"wool": {...}, "all": {...}}
            # V1: {"r,g,b,a": "id"}
            
            # Simple heuristic: Check if values are strings (ID) or dicts (Palette sub-cache)
            first_val = next(iter(raw.values())) if raw else None
            
            if isinstance(first_val, dict):
                # V2 Structure
                # Map keys back to tuples for each sub-dict
                final_cache = {}
                for mode, sub_cache in raw.items():
                    final_cache[mode] = {}
                    for k, v in sub_cache.items():
                        try:
                            parts = list(map(int, k.split(',')))
                            final_cache[mode][tuple(parts)] = v
                        except:
                            pass
                print(f"Loaded V2 cache with modes: {list(final_cache.keys())}")
                return final_cache
            else:
                # V1 Structure - Assume it belongs to 'all' or migration needed
                # For compatibility, let's just return it as 'mixed' or 'all' if we were strictly v2
                # But to avoid data loss, let's rename it or just load it into "all" and "mixed"?
                print("Detected Legacy V1 Cache. Migrating to 'all' and 'mixed'...")
                
                converted = {}
                for k, v in raw.items():
                    try:
                        parts = list(map(int, k.split(',')))
                        converted[tuple(parts)] = v
                    except:
                        pass
                        
                # Return standardized V2 structure
                return {
                    "all": converted.copy(),
                    "mixed": converted.copy() 
                }
                
        except Exception as e:
            print(f"Failed to load cache: {e}")
            return {}

    def save_cache_to_disk(self, path: str, cache: dict):
        import json
        try:
            # Expecting cache to be V2: { mode: { (r,g,b,a): id } }
            
            raw_node = {}
            
            for mode, sub_cache in cache.items():
                raw_node[mode] = {}
                for k, v in sub_cache.items():
                    # k is tuple (r,g,b,a)
                    k_str = f"{k[0]},{k[1]},{k[2]},{k[3]}"
                    raw_node[mode][k_str] = v
                    
            with open(path, 'w') as f:
                json.dump(raw_node, f)
            print(f"Saved cache to {path}.")
        except Exception as e:
            print(f"Failed to save cache: {e}")

    @staticmethod
    def rgb_to_lab(r, g, b):
        # RGB to XYZ
        def pivot_rgb(n):
            n /= 255.0
            return ((n + 0.055) / 1.055) ** 2.4 if n > 0.04045 else n / 12.92
            
        x = pivot_rgb(r) * 0.4124 + pivot_rgb(g) * 0.3576 + pivot_rgb(b) * 0.1805
        y = pivot_rgb(r) * 0.2126 + pivot_rgb(g) * 0.7152 + pivot_rgb(b) * 0.0722
        z = pivot_rgb(r) * 0.0193 + pivot_rgb(g) * 0.1192 + pivot_rgb(b) * 0.9505
        
        # XYZ to Lab
        def pivot_xyz(n):
            return n ** (1/3) if n > 0.008856 else (7.787 * n) + (16/116)
            
        # Reference White (D65)
        xn, yn, zn = 0.95047, 1.00000, 1.08883
        
        l = 116 * pivot_xyz(y / yn) - 16
        a_val = 500 * (pivot_xyz(x / xn) - pivot_xyz(y / yn))
        b_val = 200 * (pivot_xyz(y / yn) - pivot_xyz(z / zn))
        
        return (l, a_val, b_val)
