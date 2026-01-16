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
        Creates a sword model attached to the given parent node (e.g., RightArmJoint).
        The sword is positioned as if held in the hand.
        """
        blade_color = ItemFactory.COLORS.get(material, ItemFactory.COLORS["iron"])
        handle_color = ItemFactory.COLORS["stick"]
        guard_color = blade_color # Usually same as blade or material specific
        
        parts = []
        
        # Sword Geometry (Simplified 1:1 scale)
        # Held in hand. Hand is at (4,0) to (8,4) in Arm space?
        # Arm is 4x12x4. Local coords: 0..4, 0..12, 0..4.
        # Hand is usually at the bottom (Y=0..4 if shoulder is Y=12).
        # We need to anchor item to the Hand area.
        # Let's pivot at (2, 2, 2) of the hand (Center of bottom 4x4x4 cube).
        # Arm Node origin is Shoulder. Hand is Y=-10 relative to Shoulder? 
        # Wait, BoxPart Y goes UP?
        # In Rig: Arm Y len=12. Pivot (Shoulder) is Top.
        # So Hand is at Y=0..4 (if Arm is 0..12).
        # Let's assume Grab Point is (2, 2, 2).
        
        # Sword Structure:
        # Handle: 1x3x1
        # Guard: 3x1x1
        # Blade: 1x8x1
        
        # Local Offsets from Hand Center
        
        # Handle (Stick)
        parts.append(BoxPart(
            name=f"{material}_sword_handle",
            min_point=(1.5, -2, 1.5), # Stick slightly out bottom
            max_point=(2.5, 3, 2.5),
            texture_coords=(0,0), # Dummy
            color=handle_color,
            parent=parent
        ))
        
        # Guard
        parts.append(BoxPart(
            name=f"{material}_sword_guard",
            min_point=(0.5, 3, 1.5),
            max_point=(3.5, 4, 2.5),
            texture_coords=(0,0),
            color=guard_color,
            parent=parent
        ))
        
        # Blade
        parts.append(BoxPart(
            name=f"{material}_sword_blade",
            min_point=(1.5, 4, 1.5),
            max_point=(2.5, 12, 2.5), 
            texture_coords=(0,0),
            color=blade_color,
            parent=parent
        ))
        
        return parts

    @staticmethod
    def create_bow(parent: Node) -> list[BoxPart]:
        """
        Creates a bow model.
        """
        wood_color = ItemFactory.COLORS["bow_wood"]
        string_color = ItemFactory.COLORS["string"]
        parts = []
        
        # Bow Shape (Curved D)
        # Held in middle.
        
        # Central Grip
        parts.append(BoxPart(name="bow_grip", min_point=(1.5, 1, 1.5), max_point=(2.5, 3, 2.5), color=wood_color, parent=parent))
        
        # Upper Limb
        parts.append(BoxPart(name="bow_upper_1", min_point=(1.5, 3, 1.5), max_point=(2.5, 5, 2.0), color=wood_color, parent=parent))
        parts.append(BoxPart(name="bow_upper_2", min_point=(1.5, 5, 1.0), max_point=(2.5, 7, 1.5), color=wood_color, parent=parent))
        
        # Lower Limb
        parts.append(BoxPart(name="bow_lower_1", min_point=(1.5, -1, 1.5), max_point=(2.5, 1, 2.0), color=wood_color, parent=parent))
        parts.append(BoxPart(name="bow_lower_2", min_point=(1.5, -3, 1.0), max_point=(2.5, -1, 1.5), color=wood_color, parent=parent))
        
        # String
        parts.append(BoxPart(name="bow_string", min_point=(1.8, -3, 1), max_point=(2.2, 7, 1.2), color=string_color, parent=parent))
        
        return parts
