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
        """
        blade_color = ItemFactory.COLORS.get(material, ItemFactory.COLORS["iron"])
        handle_color = ItemFactory.COLORS["stick"]
        guard_color = blade_color 
        
        parts = []
        
        # Helper to create box from min/max relative bounds
        def make_part(name, min_p, max_p, col):
            w = max_p[0] - min_p[0]
            h = max_p[1] - min_p[1]
            d = max_p[2] - min_p[2]
            bp = BoxPart(name, size=(w, h, d), color=col, parent=parent)
            bp.origin = min_p # Set origin to min point relative to parent
            return bp
        
        # Handle (Stick): 1x5x1
        parts.append(make_part(f"{material}_sword_handle", (1.5, -2, 1.5), (2.5, 3, 2.5), handle_color))
        
        # Guard: 3x1x1
        parts.append(make_part(f"{material}_sword_guard", (0.5, 3, 1.5), (3.5, 4, 2.5), guard_color))
        
        # Blade: 1x8x1
        parts.append(make_part(f"{material}_sword_blade", (1.5, 4, 1.5), (2.5, 12, 2.5), blade_color))
        
        return parts

    @staticmethod
    def create_bow(parent: Node) -> list[BoxPart]:
        """
        Creates a bow model.
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
        
        # Grip
        parts.append(make_part("bow_grip", (1.5, 1, 1.5), (2.5, 3, 2.5), wood_color))
        
        # Limbs
        parts.append(make_part("bow_upper_1", (1.5, 3, 1.5), (2.5, 5, 2.0), wood_color))
        parts.append(make_part("bow_upper_2", (1.5, 5, 1.0), (2.5, 7, 1.5), wood_color))
        
        parts.append(make_part("bow_lower_1", (1.5, -1, 1.5), (2.5, 1, 2.0), wood_color))
        parts.append(make_part("bow_lower_2", (1.5, -3, 1.0), (2.5, -1, 1.5), wood_color))
        
        # String
        parts.append(make_part("bow_string", (1.8, -3, 1), (2.2, 7, 1.2), string_color))
        
        return parts
