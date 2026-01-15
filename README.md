# Skin2Schematic

**Skin2Schematic** is a Python tool that converts Minecraft Java Edition skins into 1:1 scale standing statues in `.litematic` format. It supports local files, URLs, and Minecraft usernames.

## Features

- **1:1 Scale**: 1 pixel equals 1 block.
- **Model Detection**: Automatically detects Classic (Steve) vs. Slim (Alex) arm models.
- **Full Layer Support**: Generates the base body and the outer overlay (hat, jacket, sleeves, pants) as a 1-block-thick shell.
- **Smart Color Matching**: Maps skin colors to Minecraft blocks using configurable palettes (Mixed, Concrete, Wool, Terracotta).
- **Metadata**: Includes author and timestamp in the schematic file.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/skin2schematic.git
    cd skin2schematic
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Dependencies: `Pillow`, `requests`, `litemapy`*

## Usage

Basic usage via Command Line Interface (CLI):

```bash
python src/main.py <input> [options]
```

### Examples

**1. From a Minecraft Username:**
```bash
python src/main.py Notch
```
*Creates `Notch_statue.litematic`.*

**2. From a Local File:**
```bash
python src/main.py skins/my_skin.png
```

**3. Specific Palette:**
```bash
python src/main.py Notch --palette concrete
```

### Options

- `input`: Skin source (File path, URL, or Username).
- `-o`, `--output`: Output filename (optional).
- `-p`, `--palette`: Block palette to use. Options: `mixed` (default), `concrete`, `wool`, `terracotta`.
- `-m`, `--model`: Force specific model. Options: `auto` (default), `classic`, `slim`.

## Implementation Details

- **SkinLoader**: Handles fetching from Mojang API or loading local files.
- **Geometry**: Maps the 2D skin texture to 3D block coordinates, handling the offsets for overlays.
- **ColorMatcher**: Uses Euclidean distance to find the closest matching Minecraft block from the selected palette.
- **SchematicBuilder**: Uses `litemapy` to generate mod-compatible `.litematic` files.

## License

MIT
