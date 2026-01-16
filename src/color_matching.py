import math

class ColorMatcher:
    # Palette definitions (Approximate average RGB)
    PALETTES = {
        "concrete": {
            "minecraft:white_concrete": (207, 213, 214),
            "minecraft:orange_concrete": (224, 97, 1),
            "minecraft:magenta_concrete": (169, 48, 159),
            "minecraft:light_blue_concrete": (35, 137, 199),
            "minecraft:yellow_concrete": (241, 175, 21),
            "minecraft:lime_concrete": (94, 169, 24),
            "minecraft:pink_concrete": (213, 101, 143),
            "minecraft:gray_concrete": (54, 57, 61),
            "minecraft:light_gray_concrete": (125, 125, 115),
            "minecraft:cyan_concrete": (21, 119, 136),
            "minecraft:purple_concrete": (100, 31, 156),
            "minecraft:blue_concrete": (44, 46, 143),
            "minecraft:brown_concrete": (96, 59, 31),
            "minecraft:green_concrete": (73, 91, 36),
            "minecraft:red_concrete": (142, 32, 32),
            "minecraft:black_concrete": (8, 10, 15),
        },
        "wool": {
            "minecraft:white_wool": (233, 236, 236),
            "minecraft:orange_wool": (240, 118, 19),
            "minecraft:magenta_wool": (189, 68, 179),
            "minecraft:light_blue_wool": (58, 175, 217),
            "minecraft:yellow_wool": (248, 197, 39),
            "minecraft:lime_wool": (112, 185, 25),
            "minecraft:pink_wool": (237, 141, 172),
            "minecraft:gray_wool": (62, 68, 71),
            "minecraft:light_gray_wool": (142, 142, 134),
            "minecraft:cyan_wool": (21, 137, 145),
            "minecraft:purple_wool": (121, 42, 172),
            "minecraft:blue_wool": (53, 57, 157),
            "minecraft:brown_wool": (114, 71, 40),
            "minecraft:green_wool": (84, 109, 27),
            "minecraft:red_wool": (160, 39, 34),
            "minecraft:black_wool": (20, 21, 25),
        },
        "terracotta": {
            "minecraft:terracotta": (152, 93, 67),
            "minecraft:white_terracotta": (209, 177, 161),
            "minecraft:orange_terracotta": (160, 83, 37),
            "minecraft:magenta_terracotta": (149, 87, 108),
            "minecraft:light_blue_terracotta": (112, 108, 138),
            "minecraft:yellow_terracotta": (186, 133, 36),
            "minecraft:lime_terracotta": (103, 117, 53),
            "minecraft:pink_terracotta": (160, 77, 78),
            "minecraft:gray_terracotta": (57, 41, 35),
            "minecraft:light_gray_terracotta": (135, 107, 98),
            "minecraft:cyan_terracotta": (87, 92, 92),
            "minecraft:purple_terracotta": (118, 69, 86),
            "minecraft:blue_terracotta": (74, 60, 91),
            "minecraft:brown_terracotta": (77, 51, 36),
            "minecraft:green_terracotta": (76, 82, 42),
            "minecraft:red_terracotta": (142, 60, 46),
            "minecraft:black_terracotta": (37, 22, 16),
        }
    }

    def __init__(self, mode="mixed"):
        self.palette = {}
        if mode == "mixed":
            self.palette.update(self.PALETTES["concrete"])
            self.palette.update(self.PALETTES["wool"])
            self.palette.update(self.PALETTES["terracotta"])
        elif mode in self.PALETTES:
            self.palette = self.PALETTES[mode]
        else:
            self.palette.update(self.PALETTES["concrete"])
            self.palette.update(self.PALETTES["wool"])
            
        # Precompute RGB -> Lab for palette
        self.palette_lab = {}
        for block_id, rgb in self.palette.items():
            self.palette_lab[block_id] = self.rgb_to_lab(*rgb)

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
