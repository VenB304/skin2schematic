from typing import Dict, Any
from .rig import Rig
from .primitives import Node

class PoseApplicator:
    @staticmethod
    @staticmethod
    def apply_pose(rig: Rig, pose_data: Dict[str, Dict[str, Any]]):
        """
        Applies rotations and positions to the Rig's nodes.
        Format:
        {
            "HeadJoint": {"rot": {"x": 0, "y": 0, "z": 0}, "pos": {"x": 0, "y": 0, "z": 0}},
            ...
        }
        Legacy Format (Backwards compat):
        {
            "HeadJoint": {"x": 0, "y": 0, "z": 0} (assumed rot)
        }
        """
        
        nodes_map = {}
        def traverse(node: Node):
            nodes_map[node.name] = node
            for child in node.children:
                traverse(child)
        
        traverse(rig.root)
        
        for part_name, data in pose_data.items():
            if part_name in nodes_map:
                node = nodes_map[part_name]
                
                # Check format
                if "x" in data and "rot" not in data:
                    # Legacy flat rotation
                    node.rotation = (data.get("x", 0.0), data.get("y", 0.0), data.get("z", 0.0))
                else:
                    # New format
                    if "rot" in data:
                        rot = data["rot"]
                        node.rotation = (rot.get("x", 0.0), rot.get("y", 0.0), rot.get("z", 0.0))
                    
                    if "pos" in data:
                        pos = data["pos"]
                        # Apply relative to default? 
                        # Usually pose overwrites current state. 
                        # But Node.origin is the "Bind Pose".
                        # Animators usually ADD offset to Bind Pose.
                        # Since we don't store Bind Pose separately in Node (Node.origin IS the prop),
                        # determining "Bind Pose" is hard unless Rig resets it every frame.
                        # For this simple tool, we assume 'pos' IS the target local origin.
                        # But 'Rig' sets the Bind Pose origin in constructor.
                        # So 'pose' data should probably be an OFFSET?
                        # Or specific absolute Override.
                        # Let's use Override. The T-Pose needs specific coordinates.
                        # But we need to know the 'Joint' Pivot...
                        # Rig sets r_arm at (4, 12, 0).
                        # T-Pose needs (4, 12, 0) + (0, -4, 0) = (4, 8, 0).
                        # Let's provide Absolute Position.
                        node.origin = (pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0))
                        
            else:
                print(f"Warning: Pose references unknown part '{part_name}'")

    @staticmethod
    def get_standing_pose() -> Dict[str, Any]:
        return {} 

    @staticmethod
    def get_t_pose() -> Dict[str, Any]:
        # Rig Default: Pivot Y=24 (Local 12).
        # T-Pose needs Height 20..24.
        # Rot 90 gives 24..28.
        # Shift Y -4.
        # Pivot was (4, 12, 0). New Pivot (4, 8, 0).
        return {
            "RightArmJoint": {
                "rot": {"z": 90},
                "pos": {"x": 4, "y": 8, "z": 0} 
            },
            "LeftArmJoint": {
                "rot": {"z": -90},
                "pos": {"x": -4, "y": 8, "z": 0} 
            }
        }
