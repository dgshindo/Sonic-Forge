from PIL import Image

img = Image.open("SonicForge.ico")

img.save(
    "SonicForge.ico",
    format="ICO",
    sizes=[
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256)
    ]
)

print("Icon created successfully!")