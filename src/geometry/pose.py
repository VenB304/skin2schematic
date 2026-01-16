from typing import Dict, Any
from .rig import Rig
from .primitives import Node

class PoseApplicator:
    @staticmethod
    def apply_pose(rig: Rig, pose_data: Dict[str, Dict[str, float]]):
        """
        Applies rotations to the Rig's nodes based on pose_data.
        Format:
        {
            "HeadJoint": {"x": 0, "y": 45, "z": 0},
            "RightArmJoint": {"x": -90, "y": 0, "z": 0}
        }
        """
        
        # Traverse rig and apply
        # We need to find nodes by name.
        # Rig doesn't index joints linearly, but we can traverse from root.
        
        nodes_map = {}
        def traverse(node: Node):
            nodes_map[node.name] = node
            for child in node.children:
                traverse(child)
        
        traverse(rig.root)
        
        for part_name, rot in pose_data.items():
            if part_name in nodes_map:
                node = nodes_map[part_name]
                rx = rot.get("x", 0.0)
                ry = rot.get("y", 0.0)
                rz = rot.get("z", 0.0)
                node.rotation = (rx, ry, rz)
            else:
                print(f"Warning: Pose references unknown part '{part_name}'")

    @staticmethod
    def get_standing_pose() -> Dict[str, Dict[str, float]]:
        return {} # Identity

    @staticmethod
    def get_t_pose() -> Dict[str, Dict[str, float]]:
        # Assuming Standing is arms down.
        # "T-Pose" raises arms 90 degrees?
        # Standard Rig Right Arm: Down (-Y).
        # To make T-Pose (Point +X): Rotate Z axis?
        # Right Arm Joint: Z axis rotates around Forward (Z).
        # Check coordinates.
        # Right Arm (Starboard). Z axis points Front?
        # Rotation +Z => CCW? 
        # Needs trial or standard convention.
        # Let's assume standard Euler.
        return {
            "RightArmJoint": {"z": 90}, 
            "LeftArmJoint": {"z": -90}
        }
