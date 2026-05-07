from PIL import Image

def create_transparent_icon(output_path):
    # Create a 256x256 transparent image
    size = (256, 256)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    # Save as .ico
    image.save(output_path, format="ICO")
    print(f"Transparent icon created at: {output_path}")

if __name__ == "__main__":
    create_transparent_icon("transparent.ico")
