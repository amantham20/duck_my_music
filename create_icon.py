"""
Generate icon.ico for the Duck My Music application.
Run this script to create the icon file.
"""

from PIL import Image, ImageDraw


def create_icon(size: int = 256) -> Image.Image:
    """Create the Duck My Music icon."""
    # Create a high-resolution icon
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Spotify green color
    fill_color = (29, 185, 84, 255)
    
    # Draw a circular background
    margin = size // 16
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(30, 30, 30, 255))
    
    # Draw speaker icon
    speaker_margin = size // 4
    
    # Speaker body (rectangle)
    body_left = speaker_margin
    body_right = size // 3 + size // 16
    body_top = size // 3 + size // 16
    body_bottom = 2 * size // 3 - size // 16
    draw.rectangle([body_left, body_top, body_right, body_bottom], fill=fill_color)
    
    # Speaker cone (polygon)
    cone_points = [
        (body_right, body_top - size // 16),
        (size // 2 + size // 16, speaker_margin + size // 16),
        (size // 2 + size // 16, size - speaker_margin - size // 16),
        (body_right, body_bottom + size // 16)
    ]
    draw.polygon(cone_points, fill=fill_color)
    
    # Sound waves (arcs)
    wave_center_x = size // 2 + size // 8
    wave_center_y = size // 2
    
    for i in range(1, 4):
        arc_radius = size // 8 + (i * size // 10)
        bbox = [
            wave_center_x - arc_radius,
            wave_center_y - arc_radius,
            wave_center_x + arc_radius,
            wave_center_y + arc_radius
        ]
        # Draw arc
        draw.arc(bbox, -50, 50, fill=fill_color, width=max(4, size // 32))
    
    return image


def main():
    """Generate icon files."""
    # Create icons at different sizes for ICO file
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    
    for size in sizes:
        icon = create_icon(size)
        icons.append(icon)
    
    # Save as ICO file with multiple sizes
    icons[0].save(
        'icon.ico',
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:]
    )
    
    print("Created icon.ico successfully!")
    
    # Also save a PNG for other uses
    large_icon = create_icon(512)
    large_icon.save('icon.png', format='PNG')
    print("Created icon.png successfully!")


if __name__ == '__main__':
    main()
