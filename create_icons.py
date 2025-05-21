import os
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets', 'icons')
ICON_SIZES = [
    (20, 20),
    (29, 29),
    (40, 40),
    (60, 60),
    (76, 76),
    (83, 83),  # Will save as 83.5x83.5
    (1024, 1024)
]
BG_COLOR = "#4a6f91"  # A nice blue color
FG_COLOR = "#ffffff"  # White text

def ensure_dir_exists(dir_path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def get_font(size):
    """Try to load a nice font, or fall back to default."""
    try:
        # Try to use a nice sans-serif font
        return ImageFont.truetype("Arial.ttf", size)
    except IOError:
        # Fall back to default
        return ImageFont.load_default()

def create_icon(size, text="BGG"):
    """Create an icon with the given size."""
    img = Image.new('RGB', size, BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Calculate font size based on icon size
    font_size = int(size[0] * 0.4)
    font = get_font(font_size)
    
    # Calculate text position to center it
    text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:4]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    
    # Draw the text
    draw.text(position, text, font=font, fill=FG_COLOR)
    
    return img

def main():
    # Ensure assets directory exists
    ensure_dir_exists(ASSETS_DIR)
    
    # Create app icon
    for width, height in ICON_SIZES:
        # Special case for 83.5
        if width == 83:
            width = height = 83.5
            
        icon = create_icon((int(width), int(height)))
        
        # Generate filename
        if width == 83.5:
            filename = f"app-icon-{width}.png"
        else:
            filename = f"app-icon-{width}.png"
            
        filepath = os.path.join(ASSETS_DIR, filename)
        icon.save(filepath)
        print(f"Created icon: {filepath}")
    
    # Also create the default app-icon.png
    create_icon((1024, 1024)).save(os.path.join(ASSETS_DIR, "app-icon.png"))
    print(f"Created main app icon: {os.path.join(ASSETS_DIR, 'app-icon.png')}")

if __name__ == "__main__":
    main()