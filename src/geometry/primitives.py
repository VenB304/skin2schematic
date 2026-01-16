import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class PixelBlock:
    x: int
    y: int
    z: int
    r: int
    g: int
    b: int
    a: int


# --- Matrix Math Helpers (Row Major) ---
# A Matrix is a tuple of 16 floats.
Matrix = Tuple[float, ...]

def identity_matrix() -> Matrix:
    return (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    )

def multiply_matrix(a: Matrix, b: Matrix) -> Matrix:
    # 4x4 multiplication: C = A * B
    # c_ij = sum(a_ik * b_kj)
    res = [0.0] * 16
    for row in range(4):
        for col in range(4):
            sum_val = 0.0
            for k in range(4):
                sum_val += a[row * 4 + k] * b[k * 4 + col]
            res[row * 4 + col] = sum_val
    return tuple(res)

def translation_matrix(x: float, y: float, z: float) -> Matrix:
    return (
        1.0, 0.0, 0.0, x,
        0.0, 1.0, 0.0, y,
        0.0, 0.0, 1.0, z,
        0.0, 0.0, 0.0, 1.0
    )

def rotation_matrix(rx: float, ry: float, rz: float) -> Matrix:
    # Euler angles in degrees. Order: X -> Y -> Z (Standard usually)
    pass
    # Helper to create X, Y, Z matrices
    rad_x, rad_y, rad_z = math.radians(rx), math.radians(ry), math.radians(rz)
    
    cx, sx = math.cos(rad_x), math.sin(rad_x)
    cy, sy = math.cos(rad_y), math.sin(rad_y)
    cz, sz = math.cos(rad_z), math.sin(rad_z)
    
    # Rx
    mx = (
        1.0, 0.0, 0.0, 0.0,
        0.0, cx, -sx, 0.0,
        0.0, sx, cx, 0.0,
        0.0, 0.0, 0.0, 1.0
    )
    # Ry
    my = (
        cy, 0.0, sy, 0.0,
        0.0, 1.0, 0.0, 0.0,
        -sy, 0.0, cy, 0.0,
        0.0, 0.0, 0.0, 1.0
    )
    # Rz
    mz = (
        cz, -sz, 0.0, 0.0,
        sz, cz, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    )
    
    # Combined Rz * Ry * Rx (Intrinsic vs Extrinsic? Let's check generally accepted ordering)
    # Often T * Rz * Ry * Rx
    
    temp = multiply_matrix(my, mx)
    return multiply_matrix(mz, temp)

def invert_affine_matrix(m: Matrix) -> Matrix:
    # Assumes valid affine matrix (bottom row 0,0,0,1)
    # R | T
    # 0 | 1
    # Inv is:
    # R^T | -R^T * T
    # 0   | 1
    
    # Extract R (3x3)
    r00, r01, r02 = m[0], m[1], m[2]
    r10, r11, r12 = m[4], m[5], m[6]
    r20, r21, r22 = m[8], m[9], m[10]
    
    # Extract T
    tx, ty, tz = m[3], m[7], m[11]
    
    # Transpose R
    inv_r00, inv_r01, inv_r02 = r00, r10, r20
    inv_r10, inv_r11, inv_r12 = r01, r11, r21
    inv_r20, inv_r21, inv_r22 = r02, r12, r22
    
    # New T = -R^T * T
    new_tx = -(inv_r00 * tx + inv_r01 * ty + inv_r02 * tz)
    new_ty = -(inv_r10 * tx + inv_r11 * ty + inv_r12 * tz)
    new_tz = -(inv_r20 * tx + inv_r21 * ty + inv_r22 * tz)
    
    return (
        inv_r00, inv_r01, inv_r02, new_tx,
        inv_r10, inv_r11, inv_r12, new_ty,
        inv_r20, inv_r21, inv_r22, new_tz,
        0.0, 0.0, 0.0, 1.0
    )

def transform_point(m: Matrix, x: float, y: float, z: float) -> Tuple[float, float, float]:
    # P_new = M * P
    nx = m[0]*x + m[1]*y + m[2]*z + m[3]
    ny = m[4]*x + m[5]*y + m[6]*z + m[7]
    nz = m[8]*x + m[9]*y + m[10]*z + m[11]
    # w = m[12]*x ... + m[15] which is 1.0 usually
    return (nx, ny, nz)

# --- Primitives ---

class Node:
    def __init__(self, name: str, parent: Optional['Node'] = None):
        self.name = name
        self.parent = parent
        self.children: List['Node'] = []
        
        # Local Transform Properties
        self.origin: Tuple[float, float, float] = (0.0, 0.0, 0.0) # Pivot point relative to parent
        self.rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0) # Euler Degrees (X, Y, Z)
        self.scale: float = 1.0 # Uniform scale (mostly for overlays)
        
        if parent:
            parent.add_child(self)
            
    def add_child(self, child: 'Node'):
        if child not in self.children:
            self.children.append(child)
            child.parent = self
            
    def get_local_matrix(self) -> Matrix:
        # T * R * S
        # Translation is self.origin
        t_mat = translation_matrix(*self.origin)
        r_mat = rotation_matrix(*self.rotation)
        # We don't implement generalized scale matrix yet as we only use uniform size, 
        # but let's effectively ignore scale in matrix for now and handle box sizing separately 
        # UNLESS we want "Shrinking" boxes.
        # Overlays are often "bigger" boxes, not "scaled" space (pixels don't get bigger).
        # So scale logic might belong in the Part definition, not space transform.
        return multiply_matrix(t_mat, r_mat)

    def get_world_matrix(self) -> Matrix:
        local = self.get_local_matrix()
        if self.parent:
            parent_world = self.parent.get_world_matrix()
            return multiply_matrix(parent_world, local)
        return local
        
    def world_to_local_point(self, wx: float, wy: float, wz: float) -> Tuple[float, float, float]:
        world_mat = self.get_world_matrix()
        inv_mat = invert_affine_matrix(world_mat)
        return transform_point(inv_mat, wx, wy, wz)

@dataclass
class FaceUV:
    u: int
    v: int
    w: int
    h: int
    face_name: str # 'top', 'bottom', 'left', 'right', 'front', 'back'

class BoxPart(Node):
    def __init__(self, name: str, size: Tuple[int, int, int], uv_map: Dict[str, Tuple[int, int, int, int]], parent: Optional[Node] = None, is_overlay: bool = False):
        """
        size: (width, height, depth) in blocks
        uv_map: Dict mapping face name e.g. 'front' -> (u, v, w, h) on texture
        """
        super().__init__(name, parent)
        self.size = size # (w, h, d)
        self.uv_map = uv_map
        self.is_overlay = is_overlay
        
    def get_aabb_world(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        # Get all 8 corners in world space to find AABB
        w, h, d = self.size
        # Local corners
        corners = [
            (0,0,0), (w,0,0), (0,h,0), (0,0,d),
            (w,h,0), (w,0,d), (0,h,d), (w,h,d)
        ]
        
        world_mat = self.get_world_matrix()
        
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        
        for cx, cy, cz in corners:
            wx, wy, wz = transform_point(world_mat, cx, cy, cz)
            min_x, min_y, min_z = min(min_x, wx), min(min_y, wy), min(min_z, wz)
            max_x, max_y, max_z = max(max_x, wx), max(max_y, wy), max(max_z, wz)
            
        return (min_x, min_y, min_z), (max_x, max_y, max_z)
        
    def get_texture_coord(self, lx: float, ly: float, lz: float) -> Optional[Tuple[int, int]]:
        """
        Given LOCAL coordinates (0..w, 0..h, 0..d), return UV on texture.
        Returns None if not on a surface or out of bounds.
        """
        w, h, d = self.size
        
        # Tolerance for float errors
        epsilon = 0.001
        
        # Check bounds
        if not (-epsilon <= lx <= w + epsilon and -epsilon <= ly <= h + epsilon and -epsilon <= lz <= d + epsilon):
            return None
            
        # Determine Face
        # Prioritize faces?
        # Use classic "Unfolded Box" logic.
        
        # Front: Z = 0 (in our logic? Let's check Rig definition)
        # If we define Front as -Z or +Z? 
        # Standard: Front is usually "North"?? 
        # Helper: A generic box mapper.
        
        # We need to know WHICH face we are on.
        on_left = abs(lx) < epsilon
        on_right = abs(lx - w) < epsilon
        on_bottom = abs(ly) < epsilon
        on_top = abs(ly - h) < epsilon
        on_front = abs(lz) < epsilon # Let's assume Front is Z=0 to standard
        on_back = abs(lz - d) < epsilon
        
        # Map (face_name, u_local, v_local)
        # u_local, v_local are pixel offsets within the face on texture
        
        target_face = None
        u_off, v_off = 0, 0
        
        if on_top:
            target_face = 'top'
            # Top map: x -> x, z -> y
            u_off, v_off = lx, lz
        elif on_bottom:
            target_face = 'bottom'
            # Bottom map: x -> x, z -> y (often flipped?)
            # Let's trust standard UV layout direction
            u_off, v_off = lx, lz 
        elif on_right:
            target_face = 'right' # Right of the box (positive X)
            u_off, v_off = lz, h - ly # Z map to width, Y map to height (inverted Y)
        elif on_left:
            target_face = 'left' # Negative X
            u_off, v_off = lz, h - ly
        elif on_front:
            target_face = 'front'
            u_off, v_off = lx, h - ly
        elif on_back:
            target_face = 'back'
            u_off, v_off = lx, h - ly
            
        if target_face and target_face in self.uv_map:
            u, v, tw, th = self.uv_map[target_face]
            
            # Integerize offsets
            iu_off = int(u_off)
            iv_off = int(v_off)
            
            # Clamp to face size
            if 0 <= iu_off < tw and 0 <= iv_off < th:
                return (u + iu_off, v + iv_off)
                
        return None
