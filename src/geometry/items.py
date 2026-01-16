from .primitives import BoxPart, Node

class ItemFactory:
    """
    Generates voxel geometry for items (Swords, Bows).
    Items are constructed as a list of BoxParts, usually attached to a parent node (Hand).
    """

    COLORS = {
        "wood": (141, 118, 77),
        "stone": (131, 131, 131),
        "iron": (200, 200, 200),
        "gold": (250, 235, 41),
        "diamond": (47, 222, 216),
        "netherite": (66, 60, 63),
        "stick": (105, 78, 47),
        "string": (230, 230, 230),
        "bow_wood": (141, 118, 77)
    }

    @staticmethod
    def create_sword(material: str, parent: Node) -> list[BoxPart]:
        """
        Creates a sword model attached to the given parent node.
        Aligned along -Y (Down from hand) so it points correctly when arm is raised/rotated.
        Thickness increased to 2px for better centering in 4px hand.
        """
        blade_color = ItemFactory.COLORS.get(material, ItemFactory.COLORS["iron"])
        handle_color = ItemFactory.COLORS["stick"]
        guard_color = blade_color 
        
        parts = []
        
        # Hand is 4x4. Center is 2.0.
        # We want Item 2 wide.
        # X: 1.0 to 3.0.
        # Z: 1.0 to 3.0.
        
        # Y Axis:
        # Hand is from -12 (Bottom/Tip) to 0 (Shoulder) relative to Joint?
        # Actually Arm is 0..-12. Hand region is bottom (~ -10 to -12).
        # We want Sword to extend "Out" from bottom of hand.
        # So coords should be < -12.
        
        # Handle: Inside hand (-8) to Pommel (-13).
        # Guard: Just below hand (-13 to -14).
        # Blade: -14 to -24.
        
        def make_part(name, min_p, max_p, col):
            w = max_p[0] - min_p[0]
            h = max_p[1] - min_p[1]
            d = max_p[2] - min_p[2]
            bp = BoxPart(name, size=(w, h, d), color=col, parent=parent)
            bp.origin = min_p
            return bp
        
        # Handle (Stick): 2x5x2
        # Y: -13 to -8.
        parts.append(make_part(f"{material}_sword_handle", (1.0, -13, 1.0), (3.0, -8, 3.0), handle_color))
        
        # Guard: 4x1x4 (Full hand width?) or 3?
        # Let's make it 4x1x2? Or 4x1x1?
        # Standard sword guard is wider than blade.
        # Make it X: 0.0 to 4.0. Z: 1.0 to 3.0.
        # Y: -14 to -13.
        parts.append(make_part(f"{material}_sword_guard", (0.0, -14, 1.0), (4.0, -13, 3.0), guard_color))
        
        # Blade: 2x10x2 (Thick blade?) or 2x10x1 (Flat?)
        # User asked for "thicker".
        # Let's make it 2x10x1 (Flat in Z?) or 2x10x2 (Square?)
        # Minecraft sword is flat pixels.
        # Let's make X=2 wide, Z=1 thick?
        # X: 1.0 to 3.0.
        # Z: 1.5 to 2.5 (1 pixel thick).
        # OR Z: 1.0 to 3.0 (2 pixel thick/square).
        # User said "Thicker". Let's do 2x2 square blade to be safe and visible.
        # Y: -24 to -14.
        parts.append(make_part(f"{material}_sword_blade", (1.0, -24, 1.0), (3.0, -14, 3.0), blade_color))
        
        return parts

    @staticmethod
    def create_bow(parent: Node) -> list[BoxPart]:
        """
        Creates a bow model.
        Aligned along Local Z (Vertical relative to Forward Arm)???
        Wait. If Arm is X=90 (Forward).
        Local Y is Forward.
        Local Z is Up (if X=90 flips Y->Z?).
        RotX(90): Y->Z, Z->-Y.
        So to be Vertical Up in World, we need Local -Z.
        To be Vertical Down?
        Let's try aligning along Local Z axis (-Z to +Z).
        Length ~ 4 blocks?
        Center at Hand (-11 Y).
        
        So Y is constrained to ~ -11 (Hand).
        X is centered (1.0 to 3.0).
        Z extends.
        
        """
        wood_color = ItemFactory.COLORS["bow_wood"]
        string_color = ItemFactory.COLORS["string"]
        parts = []
        
        def make_part(name, min_p, max_p, col):
            w = max_p[0] - min_p[0]
            h = max_p[1] - min_p[1]
            d = max_p[2] - min_p[2]
            bp = BoxPart(name, size=(w, h, d), color=col, parent=parent)
            bp.origin = min_p 
            return bp
            
        # Center Point
        CY = -11.0 # Hand Y
        CX = 2.0   # Hand Center
        
        # Bow lies in X-Z plane (because Y is forward axis in world)
        # But wait. If Arm is Vertical (X=180).
        # We want Bow Vertical?
        # If Arm is Vertical, Local Y is World Up/Down (flipped).
        # So Bow along Local Y is Vertical.
        # If Arm is Horizontal (X=90).
        # Local Y is World Forward.
        # We want Bow Vertical in World (Up/Down).
        # This maps to Local Z.
        
        # So Bow Orientation depends on Pose Context?
        # Or we always hold Bow Vertical relative to gravity?
        # If I hold a bow while charging?
        # Usually Bow is held PERPENDICULAR to Forearm?
        # If Forearm is Forward, Bow is Vertical.
        # So Bow is usually aligned with Arm's Z axis.
        # (Arm Z is Left/Right or Up/Down depending on twist).
        
        # Let's align Bow along Z and see.
        
        # Grip: 2x2x2 at Center
        parts.append(make_part("bow_grip", (1.0, CY-1, -1), (3.0, CY+1, 1), wood_color))
        
        # Use Local Z for "Verticality".
        # Upper Limb (Negative Z? or Positive?)
        # RotX(90): Z -> -Y (Up).
        # So Negative Z becomes World Up.
        # Limb 1: Z -1 to -3.
        parts.append(make_part("bow_upper_1", (1.0, CY-1, -3), (3.0, CY+1, -1), wood_color))
        # Limb 2: Z -3 to -5.
        parts.append(make_part("bow_upper_2", (1.0, CY-1, -5), (3.0, CY+1, -3), wood_color))
        
        # Lower Limb (Positive Z -> World Down)
        parts.append(make_part("bow_lower_1", (1.0, CY-1, 1), (3.0, CY+1, 3), wood_color))
        parts.append(make_part("bow_lower_2", (1.0, CY-1, 3), (3.0, CY+1, 5), wood_color))
        
        # String
        # Connects Tips (-5 and 5).
        # Offset in X?
        # String is tight.
        parts.append(make_part("bow_string", (0.5, CY-0.5, -5), (1.0, CY+0.5, 5), string_color))
        
        return parts
