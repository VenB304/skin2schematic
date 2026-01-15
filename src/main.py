import argparse
import sys
import os
from skin_loader import SkinLoader
from geometry import SkinGeometry
from color_matching import ColorMatcher
from schematic_builder import SchematicBuilder

def main():
    parser = argparse.ArgumentParser(description="Convert Minecraft skin to Litematic statue.")
    parser.add_argument("input", help="Skin source: File path, URL, or Username")
    parser.add_argument("-o", "--output", help="Output file path (default: input_name.litematic)")
    parser.add_argument("-p", "--palette", choices=["mixed", "concrete", "wool", "terracotta"], default="mixed", help="Block palette to use")
    parser.add_argument("-m", "--model", choices=["auto", "classic", "slim"], default="auto", help="Skin model type")

    args = parser.parse_args()

    print(f"Loading skin from: {args.input}")
    try:
        skin_img = SkinLoader.load_skin(args.input)
    except Exception as e:
        print(f"Error loading skin: {e}")
        sys.exit(1)

    model = args.model
    if model == "auto":
        model = SkinLoader.detect_model(skin_img)
        print(f"Detected model: {model}")
    else:
        print(f"Using model: {model}")

    print("Generating geometry...")
    pixel_blocks = SkinGeometry.generate_blocks(skin_img, model=model)
    print(f"Generated {len(pixel_blocks)} pixels.")

    print(f"Matching colors (Palette: {args.palette})...")
    matcher = ColorMatcher(mode=args.palette)
    
    builder = SchematicBuilder(name=f"Statue_{args.input.split('/')[-1].split('.')[0]}", author=os.getlogin() if hasattr(os, 'getlogin') else "Skin2Schematic")
    
    added_count = 0
    for pb in pixel_blocks:
        block_id = matcher.find_nearest(pb.r, pb.g, pb.b, pb.a)
        if block_id:
            builder.add_block(pb.x, pb.y, pb.z, block_id)
            added_count += 1
            
    print(f"Mapped {added_count} blocks.")

    output_path = args.output
    if not output_path:
        base_name = os.path.basename(args.input)
        if '.' in base_name:
            base_name = base_name.rsplit('.', 1)[0]
        # Clean up username if input was username?
        if "http" in args.input:
            base_name = "downloaded_skin"
        # If input doesn't look like a file, trust basename logic or just use "output"?
        # If input is "Ven", basename is "Ven".
        output_path = f"{base_name}_statue.litematic"

    print(f"Saving to {output_path}...")
    try:
        builder.save(output_path)
    except Exception as e:
        print(f"Error saving schematic: {e}")
        sys.exit(1)

    print("Done!")

if __name__ == "__main__":
    main()
