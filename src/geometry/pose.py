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

    POSES = {
        "standing": {

        }, # Standing (Default)

        "walking": {
            # Pitch (X-axis) rotations
            "RightLegJoint": {"rot": {"x": 20}},  # Backward
            "LeftLegJoint": {"rot": {"x": -20}},  # Forward
            "RightArmJoint": {"rot": {"x": -20}}, # Forward (Opposite to leg)
            "LeftArmJoint": {"rot": {"x": 20}}    # Backward
        },

        "zombie": {
            "RightArmJoint": {
                "rot": {"x": 90},
                "pos": {"x": 4, "y": 10, "z": 2}
            },
            "LeftArmJoint": {
                "rot": {"x": 90},
                "pos": {"x": -4, "y": 10, "z": 2}
            }
        },

        "t_pose": {
            "RightArmJoint": {
                "rot": {"z": 90},
                "pos": {"x": 4, "y": 8, "z": 0} 
            },
            "LeftArmJoint": {
                "rot": {"z": -90},
                "pos": {"x": -4, "y": 8, "z": 0} 
            }
        },

        "floor_sit": {
            "RightLegJoint": {"rot": {"x": 90}},
            "LeftLegJoint": {"rot": {"x": 90}}
        },

        "chair_sit_zombie": {
            "RightLegJoint": {"rot": {"x": 90}},
            "LeftLegJoint": {"rot": {"x": 90}},
            "RightArmJoint": {
                "rot": {"x": 90},
                "pos": {"x": 4, "y": 10, "z": 2}
            },
            "LeftArmJoint": {
                "rot": {"x": 90},
                "pos": {"x": -4, "y": 10, "z": 2}
            }
        },

        "chair_sit": {
            "RightLegJoint": {"rot": {"x": 90}},
            "LeftLegJoint": {"rot": {"x": 90}},
            "RightArmJoint": {
                "rot": {"x": 45},
                "pos": {"x": 4, "y": 12, "z": 2}
            },
            "LeftArmJoint": {
                "rot": {"x": 45},
                "pos": {"x": -4, "y": 12, "z": 2}
            }
        },

        # --- Movement Mechanics ---
        "running": {
            "RightLegJoint": {"rot": {"x": 50}}, # Backward
            "LeftLegJoint": {"rot": {"x": -50}}, # Forward
            "RightArmJoint": {"rot": {"x": -50}},
            "LeftArmJoint": {"rot": {"x": 50}}
        },
        "sneaking": {
            # Fix: Lower body height + correct angle
            # User says "leaning back". So +25 was Back.
            # Changing to -25 (Forward).
            "BodyJoint": {
                "rot": {"x": -25}, 
                "pos": {"y": -2} 
            },
            "HeadJoint": {"rot": {"x": 25}},  # Look Up to compensate
            "RightLegJoint": {"rot": {"x": 25}}, 
            "LeftLegJoint": {"rot": {"x": 25}},
            "RightArmJoint": {"rot": {"x": 25}}, # Arm vertical-ish
            "LeftArmJoint": {"rot": {"x": 25}}
        },
        "flying": {
            # User: "Rotated 180 degrees except head".
            # Previous: Body 90. +X is Back. So 90 is Face Up.
            # Fix: Body -90 (Face Down).
            "BodyJoint": {"rot": {"x": -90}}, 
            "HeadJoint": {"rot": {"x": 90}}, # Look "Up" (Forward relative to world)
            "RightArmJoint": {"rot": {"x": 180}}, 
            "LeftArmJoint": {"rot": {"x": 180}},
            "RightLegJoint": {"rot": {"x": 0}}, 
            "LeftLegJoint": {"rot": {"x": 0}}
        },

        # --- Social / Emotes ---
        "waving": {
            # User: Clipping. Rotated wrong way.
            # Previous: X=170, Z=15.
            # Let's try Z-based "High Side" wave.
            # Z=135 (Diagonal Up/Right).
            "RightArmJoint": {"rot": {"z": 135},
            "pos": {"x": 4, "y": 10, "z": -2}}
        },
        "pointing": {
            "RightArmJoint": {"rot": {"x": 90},
            "pos": {"x": 4, "y": 10, "z": -2}}
        },
        "facepalm": {
            # User: "Heil Hitler" (Straight arm). Needs bend.
            # Fix: Angle shoulder UP and IN.
            # X=-90 (Forward). Z=110 (In/Up?).
            # Check Z: +Z is Out (Right). -Z is In (Left).
            # We want Right Arm to go Left (In). So -Z?
            # Or Pitch Up (-X) and Yaw Left (-Y).
            # Try: Pitch -50 (Up/Forward). Yaw -45 (Left). Roll?
            # Wait, Face is high.
            # Try: X=-150 (High Up), Z=-30 (In).
            "RightArmJoint": {
                "rot": {"x": 160, "z": 36},
                "pos": {"x": 4, "y": 8, "z": -2}}
        },
        "shrug": {
            "RightArmJoint": {"rot": {"z": 30, "x": 10}},
            "LeftArmJoint": {"rot": {"z": -30, "x": 10}} 
        },

        # --- Action / Combat ---
        "bow_aim": {
            "RightArmJoint": {
                "rot": {"x": 90, "y": 45}},
            "LeftArmJoint": {
                "rot": {"x": 90}}
        },
        "sword_charge": {
            "RightArmJoint": {"rot": {"x": 180}}
        },
        "hero_landing": {
            "BodyJoint": {"rot": {"x": -45}},
            "HeadJoint": {"rot": {"x": 45}},
            "RightLegJoint": {"rot": {"x": -60}},
            "LeftLegJoint": {"rot": {"x": 45}},
            "RightArmJoint": {"rot": {"x": 45}},
            "LeftArmJoint": {"rot": {"x": 80}}  
        }
    }

    @staticmethod
    def get_pose(name: str) -> Dict[str, Any]:
        return PoseApplicator.POSES.get(name, {})

    @staticmethod
    def get_standing_pose() -> Dict[str, Any]:
        return PoseApplicator.POSES["standing"]

    @staticmethod
    def get_t_pose() -> Dict[str, Any]:
        return PoseApplicator.POSES["tpose"]
