from typing import Dict, Tuple, List
from .primitives import Node, BoxPart

class Rig:
    def __init__(self, root: Node, parts: List[BoxPart]):
        self.root = root
        self.parts = parts
    
    def get_parts(self) -> List[BoxPart]:
        return self.parts

class RigFactory:
    """
    Constructs the Hierarchical Rig for Minecraft Characters.
    Coordinate System (Local to Rig Root which is at Ground Center):
    X: Left (-X) to Right (+X)
    Y: Down (0) to Up (+Y)
    Z: Back (-Z) to Front (+Z)
    """

    @staticmethod
    def _create_box_uv(u: int, v: int, w: int, h: int, d: int) -> Dict[str, Tuple[int, int, int, int]]:
        return {
            'top': (u + d, v, w, d),
            'bottom': (u + d + w, v, w, d),
            'right': (u, v + d, d, h), # Outer Right
            'front': (u + d, v + d, w, h),
            'left': (u + d + w, v + d, d, h),
            'back': (u + d + w + d, v + d, w, h),
        }

    @staticmethod
    def create_rig(model_type: str = "classic") -> Rig:
        root = Node("root")
        
        # We will collect parts in a specific Order for Rasterization Priority.
        # Priority: Head > Arms/Legs > Body.
        # This ensures that if a Sleeve overlaps a Jacket, the Sleeve wins.
        priority_parts: List[BoxPart] = []
        
        is_slim = (model_type == "slim")
        arm_w = 3 if is_slim else 4

        # --- NODES & HIERARCHY SETUP ---
        
        # Body Joint (Hip)
        # Pivot: Bottom of Body (Y=12)
        body_joint = Node("BodyJoint", parent=root)
        body_joint.origin = (0, 12, 0)
        
        # Head Joint (Neck)
        # Pivot: Top of Body relative to BodyJoint (Y=12)
        head_joint = Node("HeadJoint", parent=body_joint)
        head_joint.origin = (0, 12, 0)
        
        # Arm Joints (Shoulders)
        # Pivot Logic:
        # To ensure the Top Face of a rotated arm (T-Pose) is flush with the Top of Body (Global Y=24),
        # we must lower the pivot.
        # Rotated Arm Height = Arm Width (Rotation X->Y).
        # We want Rotated Top to be at Y=24.
        # Rotated Top = Pivot Y + Arm Width.
        # So Pivot Y = 24 - Arm Width.
        # Relative to BodyJoint (Y=12): Pivot Local Y = 12 - Arm Width.
        
        pivot_y_local = 12 - arm_w
        
        # Right Arm Joint
        r_arm_joint = Node("RightArmJoint", parent=body_joint)
        r_arm_joint.origin = (4, pivot_y_local, 0)
        
        l_arm_joint = Node("LeftArmJoint", parent=body_joint)
        l_arm_joint.origin = (-4, pivot_y_local, 0)
        
        # Leg Joints (Hips)
        # Pivot: Center of Leg Top relative to BodyJoint (Y=0).
        # Right Leg (classic) is centered at X=2.
        r_leg_joint = Node("RightLegJoint", parent=body_joint)
        r_leg_joint.origin = (2, 0, 0)
        
        l_leg_joint = Node("LeftLegJoint", parent=body_joint)
        l_leg_joint.origin = (-2, 0, 0)
        
        # --- PARTS DEFINITION & APPENDING (Priority Order) ---
        
        # 1. HEAD & HAT (Highest Priority)
        head_uv = RigFactory._create_box_uv(0, 0, 8, 8, 8)
        head = BoxPart("Head", (8, 8, 8), head_uv, parent=head_joint)
        head.origin = (-4, 0, -4)
        priority_parts.append(head)
        
        hat_uv = RigFactory._create_box_uv(32, 0, 8, 8, 8)
        hat = BoxPart("Hat", (10, 10, 10), hat_uv, parent=head_joint, is_overlay=True)
        hat.origin = (-5, -1, -5)
        priority_parts.append(hat)
        
        # 2. ARMS (Sleeves > Base)
        # Right Arm
        # Pivot Y is lowered by arm_w.
        # But Upright Arm must still extend from Y=12 to Y=24 (Global).
        # Relative to Pivot (Y = 24 - arm_w):
        # Top (24) is at y = arm_w.
        # Bottom (12) is at y = 12 - (24 - arm_w) = arm_w - 12.
        # So Y range: [arm_w - 12, arm_w].
        # Length is 12. Correct.
        # Origin Y = arm_w - 12.
        # E.g. Classic: arm_w=4. Origin Y = 4-12 = -8. Range -8..4.
        r_arm_uv = RigFactory._create_box_uv(40, 16, arm_w, 12, 4)
        r_arm = BoxPart("RightArm", (arm_w, 12, 4), r_arm_uv, parent=r_arm_joint)
        r_arm.origin = (0, arm_w - 12, -2) 
        priority_parts.append(r_arm)
        
        r_sleeve_uv = RigFactory._create_box_uv(40, 32, arm_w, 12, 4)
        r_sleeve = BoxPart("RightSleeve", (arm_w + 2, 14, 6), r_sleeve_uv, parent=r_arm_joint, is_overlay=True)
        r_sleeve.origin = (-1, arm_w - 12 - 1, -3) # Expands by 1
        priority_parts.append(r_sleeve)
        
        # Left Arm
        l_arm_uv = RigFactory._create_box_uv(32, 48, arm_w, 12, 4)
        l_arm = BoxPart("LeftArm", (arm_w, 12, 4), l_arm_uv, parent=l_arm_joint)
        l_arm.origin = (-arm_w, arm_w - 12, -2) 
        priority_parts.append(l_arm)
        
        l_sleeve_uv = RigFactory._create_box_uv(48, 48, arm_w, 12, 4)
        l_sleeve = BoxPart("LeftSleeve", (arm_w + 2, 14, 6), l_sleeve_uv, parent=l_arm_joint, is_overlay=True)
        l_sleeve.origin = (-arm_w - 1, arm_w - 12 - 1, -3)
        priority_parts.append(l_sleeve)
        
        # 3. LEGS
        # Right Leg (Pivot X=2).
        # Leg is 4 wide. Centered on 2 -> 0..4.
        # Relative to 2: -2..2.
        r_leg_uv = RigFactory._create_box_uv(0, 16, 4, 12, 4)
        r_leg = BoxPart("RightLeg", (4, 12, 4), r_leg_uv, parent=r_leg_joint)
        r_leg.origin = (-2, -12, -2)
        priority_parts.append(r_leg)
        
        r_pants_uv = RigFactory._create_box_uv(0, 32, 4, 12, 4)
        r_pants = BoxPart("RightPants", (6, 14, 6), r_pants_uv, parent=r_leg_joint, is_overlay=True)
        r_pants.origin = (-3, -13, -3)
        priority_parts.append(r_pants)
        
        # Left Leg (Pivot X=-2)
        l_leg_uv = RigFactory._create_box_uv(16, 48, 4, 12, 4)
        l_leg = BoxPart("LeftLeg", (4, 12, 4), l_leg_uv, parent=l_leg_joint)
        l_leg.origin = (-2, -12, -2)
        priority_parts.append(l_leg)
        
        l_pants_uv = RigFactory._create_box_uv(0, 48, 4, 12, 4)
        l_pants = BoxPart("LeftPants", (6, 14, 6), l_pants_uv, parent=l_leg_joint, is_overlay=True)
        l_pants.origin = (-3, -13, -3)
        priority_parts.append(l_pants)
        
        # 4. BODY (Lowest Priority covers/base)
        body_uv = RigFactory._create_box_uv(16, 16, 8, 12, 4)
        body = BoxPart("Body", (8, 12, 4), body_uv, parent=body_joint)
        body.origin = (-4, 0, -2)
        priority_parts.append(body)
        
        jacket_uv = RigFactory._create_box_uv(16, 32, 8, 12, 4)
        jacket = BoxPart("Jacket", (10, 14, 6), jacket_uv, parent=body_joint, is_overlay=True)
        jacket.origin = (-5, -1, -3)
        priority_parts.append(jacket)

        return Rig(root, priority_parts)
