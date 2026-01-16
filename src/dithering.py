import numpy as np

class Ditherer:
    # 8x8 Bayer Matrix
    BAYER_8 = np.array([
        [ 0, 32,  8, 40,  2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44,  4, 36, 14, 46,  6, 38],
        [60, 28, 52, 20, 62, 30, 54, 22],
        [ 3, 35, 11, 43,  1, 33,  9, 41],
        [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47,  7, 39, 13, 45,  5, 37],
        [63, 31, 55, 23, 61, 29, 53, 21]
    ], dtype=np.float32) / 64.0

    @staticmethod
    def apply_bayer_dither(colors: np.ndarray, coords: np.ndarray, strength: float = 32.0) -> np.ndarray:
        """
        Applies ordered dithering to the colors array based on coords.
        colors: (N, 3) or (N, 4) uint8/float
        coords: (N, 3) int (x, y, z)
        strength: Magnitude of dithering (RGB shift)
        """
        # Ensure floats
        colors_f = colors.astype(np.float32)
        
        # We need to map 3D coords to 2D Bayer or 3D Bayer?
        # Standard approach: project X/Y or X/Z?
        # For a statue, X/Y (front view) and Z/Y (side view) matter.
        # Let's use (x + z) for horizontal, y for vertical?
        # Or simple (x % 8, y % 8) logic might create banding on Z face.
        # Better: 3D dithering or just wrap indices.
        # Let's try separate indices: x, y, z.
        
        # Simplified: Use (x ^ z) % 8, y % 8
        bx = (coords[:, 0] ^ coords[:, 2]) % 8
        by = coords[:, 1] % 8
        
        thresholds = Ditherer.BAYER_8[by, bx] # (N,)
        
        # Map 0..1 to -0.5 .. 0.5
        offsets = (thresholds - 0.5) * strength
        
        # Apply to RGB (indices 0,1,2)
        # Broadcasting offsets: (N, 1)
        colors_f[:, 0] += offsets
        colors_f[:, 1] += offsets
        colors_f[:, 2] += offsets
        
        # Clip
        np.clip(colors_f, 0, 255, out=colors_f)
        
        return colors_f.astype(np.uint8)
