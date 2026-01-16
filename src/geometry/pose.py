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
        "default": {

        }, # Standing

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

        "sitting": {
            "RightLegJoint": {"rot": {"x": 90}},
            "LeftLegJoint": {"rot": {"x": 90}}
        },

        "sitting_zombie": {
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

        "sitting_relaxed": {
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
            # Hunch: Body leans forward. In Rig, +X is Pitch Forward/Back?
            # Walking had RightLeg X=20 (Back). LeftLeg X=-20 (Forward).
            # So +X = Back. -X = Forward.
            # User says: Legs Pitch -30 (Bent forward?), Torso Pitch 30.
            # If BodyJoint rotates +30 (Back?), user might mean Leaning BACK?
            # Standard Sneak: Body leans FORWARD. 
            # If -X is Forward, Body should be -15 or -30?
            # User specs: "Torso: Pitch 30". "Legs: Pitch -30".
            # If +30 is BACK, then Torso leans BACK. This is wrong for sneak.
            # Unless user assumes +X is Forward.
            # Let's trust user numbers first? Or trust Rig convention?
            # Rig Convention (from walking): -X is Forward Swing.
            # So for Sneak (Lean Forward): Body should be -X (e.g. -15).
            # If Body is -15, Legs (child of Body) are rotated -15 in World. 
            # To be straight up, Legs must rotate +15 relative to Body.
            # User says: Torso 30, Legs -30. Maybe they mean relative to vertical?
            # If Torso is 30 (Forward?), Legs -30 (Back to vertical?).
            # I will assume User means "Visual Angle".
            # Implementation:
            # BodyJoint: rot x = -20 (Lean Forward 20 deg).
            # HeadJoint: rot x = 20 (Look Up 20 deg to level).
            # LegJoints: rot x = 20 (Rotate Back 20 deg to vertical).
            # ArmJoints: rot x = 0 (Hang vertical, so +20 relative to body?).
            # Let's try to match user intent with Rig Logic.
            
            "BodyJoint": {"rot": {"x": -15}}, # Lean Forward
            "HeadJoint": {"rot": {"x": 15}},  # Look Up
            "RightLegJoint": {"rot": {"x": 15}}, # Counter-rotate
            "LeftLegJoint": {"rot": {"x": 15}},
            "RightArmJoint": {"rot": {"x": 15}}, # Arms hang straight down (or slightly back?)
            "LeftArmJoint": {"rot": {"x": 15}}
        },
        "flying": {
            # Superman.
            # Body Horizontal.
            # If -X is Forward, -90 is Face Down?
            # Let's think: Standing (0,1,0). 
            # Rotate -90 X -> (0,0,-1). Face Down / Forward. Yes.
            "BodyJoint": {"rot": {"x": -90}}, 
            "HeadJoint": {"rot": {"x": 90}}, # Look "Up" relative to body (Forward)
            "RightArmJoint": {"rot": {"x": 180}}, # Arms extended forward (Superman)
            "LeftArmJoint": {"rot": {"x": 180}},
            "RightLegJoint": {"rot": {"x": 0}}, # Straight back
            "LeftLegJoint": {"rot": {"x": 0}}
        },

        # --- Social / Emotes ---
        "waving": {
            # R Arm: Pitch -170 (Up/Back?), Roll 20.
            # -X is Forward. -170 is almost Full Up (~180).
            # So -170 is "Arm Up". 
            # X=-170, Z=20.
            "RightArmJoint": {"rot": {"x": -170, "z": 20}}
        },
        "pointing": {
            # R Arm: Pitch -90 (Forward), Yaw 10 (Inward).
            # Y is Yaw.
            "RightArmJoint": {"rot": {"x": -90, "y": 10}}
        },
        "facepalm": {
            # R Arm: Pitch -130 (Up/Forward), Yaw -40 (Face).
            # -130 X, -40 Y.
            "RightArmJoint": {"rot": {"x": -130, "y": -40}}
        },
        "shrug": {
            # Arms: Roll 30 (Out), Pitch -10 (Forward slightly).
            # Z is Roll? Usually Z is Roll (Lateral).
            "RightArmJoint": {"rot": {"z": 30, "x": -10}},
            "LeftArmJoint": {"rot": {"z": -30, "x": -10}} # Negative Z for Left? (Mirror)
        },

        # --- Action / Combat ---
        "bow_aim": {
            "RightArmJoint": {"rot": {"x": -90, "y": 45}},
            "LeftArmJoint": {"rot": {"x": -90}}
        },
        "sword_charge": {
            # Downward Strike Prep (Arm High)
            # Pitch -180 (Full Up).
            "RightArmJoint": {"rot": {"x": -180}}
        },
        "hero_landing": {
            # 3-Point Landing.
            # Crouch Deep.
            # Body: -45 (Lean Forward).
            # R Knee Up: Requires Right Leg Forward? X=-90.
            # L Leg Back: X=45.
            # R Fist Ground: R Arm X=45 (Down/Forward) to touch ground?
            # L Arm Back: X=45.
            # Pivot Head Up: X=45.
            "BodyJoint": {"rot": {"x": -45}},
            "HeadJoint": {"rot": {"x": 45}},
            "RightLegJoint": {"rot": {"x": -60}}, # Right Knee "Up" (Leg Forward)
            "LeftLegJoint": {"rot": {"x": 45}}, # Left Leg Back
            "RightArmJoint": {"rot": {"x": 45}}, # Fist to ground? 
            "LeftArmJoint": {"rot": {"x": 80}}  # Arm back for balance
        }
    }

    @staticmethod
    def get_pose(name: str) -> Dict[str, Any]:
        return PoseApplicator.POSES.get(name, {})

    @staticmethod
    def get_standing_pose() -> Dict[str, Any]:
        return PoseApplicator.POSES["default"]

    @staticmethod
    def get_t_pose() -> Dict[str, Any]:
        return PoseApplicator.POSES["tpose"]
