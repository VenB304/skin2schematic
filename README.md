# Skin2Schematic

**Skin2Schematic** is a powerful Python tool that converts Minecraft Java Edition skins into **1:1 scale statues**, ready for building in-game via Litematica. It supports complex poses, 3D items, batch processing, and an interactive wizard.

## Features

- **1:1 Scale Statues**: 1 pixel equals 1 block.
- **Robust Pose System**: Choose from **17+ poses** including `walking`, `bow_aim`, `superman`, and `sitting`.
- **3D Items**: Statues can hold **Swords** (Wood, Stone, Iron, Gold, Diamond, Netherite) and **Bows**.
- **Interactive Wizard**: Run without arguments to launch a user-friendly menu.
- **Batch Processing**: Convert an entire folder of skins at once.
- **Smart Geometry**: 
    - **Solid Poses**: Inverse mapping voxelizer ensures gap-free solid geometry even with rotations.
    - **Auto-Grounding**: Statues are automatically aligned to the floor.
    - **Layer Support**: Handles secondary layers (hat/jacket) properly with collision priority.
- **Configuration**: Customizable block palettes via `palette.json`.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/venb/skin2schematic.git
    cd skin2schematic
    ```

2.  **Install dependencies**:
    ```bash
    pip install numpy litemapy nbtlib Pillow
    ```

## Usage

### 1. Interactive Wizard (Recommended)
Simply run the script without arguments. It will double-check your current folder for `.png` files and ask you what to do (Scan Skins -> Select Pose).
```bash
python src/main.py
```

### 2. Command Line Interface (CLI)

**Single File:**
```bash
python src/main.py -i steve.png -p walking
```

**Batch Processing (Folder):**
```bash
python src/main.py -i ./my_skins/ -o ./output/ -p bow_aim
```

**Debug Gallery:**
Generates a massive schematic containing ALL available poses and item variants for a specific skin.
```bash
python src/main.py -i steve.png --debug
```

### Options
- `-i`, `--input`: Input file (`skin.png`) or directory (`./skins`).
- `-o`, `--output`: Output file or directory (Default `output/`).
- `-p`, `--pose`: Pose name (default: `standing`).
- `--list-poses`: List all available poses.
- `--debug`: Generate debug gallery (Alias for `--pose debug_all`).
- `--palette`: Block palette (`all`, `wool`, `concrete`, `terracotta`).
- `--solid`: Disable hollow optimization (fill inside with blocks).

## Available Poses
Use `--list-poses` to see the full list.
- **Standard**: `standing`, `walking`, `zombie`, `t_pose`
- **Sitting**: `floor_sit`, `chair_sit`, `chair_sit_zombie`
- **Action**: `sword_charge` (Variants: `_diamond`, `_gold`, etc.), `bow_aim`, `hero_landing`
- **Social**: `waving`, `pointing`, `facepalm`, `shrug`
- **Movement**: `running`, `sneaking` (Crouches 1.5 blocks), `flying` (Superman)

## Configuration
Block palettes can be customized in `src/palette.json`. You can modify which blocks are used for color matching without editing Python code.
