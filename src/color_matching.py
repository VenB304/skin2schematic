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
        for block_id, rgb in self.palette.items():
            self.palette_lab[block_id] = self.rgb_to_lab(*rgb)

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
            # Just map commonly used pixels? 
            # Or iterate pixel data.
            # For simplicity, if getcolors fails (returns None), we can scan manually.
            # But 4096 is limit for 64x64. So it should always work for skins.
            pixel_data = list(image.getdata())
            unique_colors = set(pixel_data)
            for color in unique_colors:
                r, g, b, a = color
                block_id = self.find_nearest(r, g, b, a)
                if block_id:
                    mapping[color] = block_id
                    
        return mapping

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
