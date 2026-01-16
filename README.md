# Minecraft Skin-to-Statue Generator

**A powerful, optimized Python tool that converts Minecraft skins into 1:1 scale 3D `.litematic` statues.**

This tool takes any Minecraft skin (Modern or Legacy) and generates a precise 3D schematic, handling complex geometry, overlays, and poses automatically. It allows you to create massive statue galleries or single player decorations in seconds.

---

## ✨ Key Features

*   **Smart Geometry & Overlays**: Accurately handles the secondary skin layer (Jacket, Hat, Sleeves) without unsightly gaps or floating pixels.
*   **Pose System**: Built-in rigging system includes dynamic poses like *Walking*, *Running*, *Sitting*, *Zombie*, *Facepalm*, and *Hero Landing*.
*   **Legacy Support**: Automatically detects and fixes old 64x32 (pre-1.8) skins by upgrading them to 64x64 and mirroring limbs.
*   **Batch Processing**: Capable of processing folders containing thousands of skins in parallel using multi-core processing.
*   **Performance Cache**: Uses intelligent color caching to speed up block matching significantly over time.
*   **Anti-Crack Technology**: Uses 7-point oversampling to prevent "cracks" or holes in the mesh when limbs are rotated at complex angles.

---

## 🚀 Quick Start

### Prerequisites
*   Python 3.8+ installed.
*   Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Interactive Wizard (The Easy Way)
Simply run the script without arguments to launch the interactive wizard:

```bash
python src/main.py
```

Follow the prompts to:
1.  Select a skin file (or process all in the folder).
2.  Choose a pose (e.g., `standing`, `walking`).
3.  Watch it generate your `.litematic` file!

---

## 💻 Command Line Usage

For advanced users and batch operations, use the command line arguments:

| Argument | Description | Example |
| :--- | :--- | :--- |
| `-i`, `--input` | Input skin file or directory | `-i my_skin.png` or `-i ./skins/` |
| `-o`, `--output` | Output filename or directory | `-o ./statues/` |
| `-p`, `--pose` | Specific pose name to apply | `-p running` |
| `--model` | Force model type (`classic` or `slim`) | `--model slim` |
| `--solid` | Fill the inside of the statue (default is hollow) | `--solid` |
| `--debug` | Generates a "Gallery" of all poses for the skin | `--debug` |

**Example: Batch process a folder of skins into "Walking" statues:**
```bash
python src/main.py -i ./my_skins_folder/ -o ./output_folder/ -p walking
```

---

## 📚 Pose Library Reference

Use these keys with the `--pose` argument:

*   **Basics**: `standing` (Default), `t_pose`
*   **Movement**: `walking`, `running`, `sneaking`, `flying` (Superman style)
*   **Sitting**: `floor_sit`, `chair_sit`, `chair_sit_zombie`
*   **Action**: `hero_landing`, `bow_aim`, `sword_charge`
*   **Emotes**: `waving`, `pointing`, `shrug`, `facepalm`, `zombie`

*Tip: Run `python src/main.py --list-poses` to see the full up-to-date list.*

---

## 🎮 How to Import into Minecraft

1.  **Locate Output**: Find the generated `.litematic` file (e.g., `Statue_Steve_walking.litematic`).
2.  **Move to Folder**: Copy the file to your Minecraft installation's schematic folder:
    *   `%appdata%/.minecraft/schematics/` (Windows)
    *   `~/.minecraft/schematics/` (Mac/Linux)
3.  **Load in Game**:
    *   Install the **Litematica** mod for your version.
    *   Press `M` (default) to open menu → **Load Schematics**.
    *   Select your statue and place it!
    *   *Note: The anchor point is located between the statue's feet.*

---

## 🔧 Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Skin looks black/garbled** | Ensure the input is a valid Minecraft Skin (64x64 or 64x32 PNG). Non-square images or HD skins (128x128) are not currently supported. |
| **"Module not found" error** | Run `pip install -r requirements.txt` again to ensure `litemapy`, `Pillow`, and `numpy` are installed. |
| **Window closes instantly** | Open `cmd` or Terminal, navigate to the folder, and run `python src/main.py` manually to see the error message. |
| **Cracks in mesh** | This is usually fixed by the oversampling engine. If issues persist, try a simpler pose. |
