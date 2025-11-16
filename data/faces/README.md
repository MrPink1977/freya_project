# Known Faces Directory

This directory contains photos of people for facial recognition.

## Directory Structure

```
data/faces/
├── john/
│   ├── photo1.jpg
│   └── photo2.jpg
├── jane/
│   └── headshot.png
└── family/
    ├── mom.jpg
    └── dad.jpg
```

## Guidelines

1. **One face per photo** - Each image should contain only one person's face
2. **Clear, front-facing** - Best results with clear, well-lit, front-facing photos
3. **Organize by person** - Create subdirectories for each person
4. **Supported formats**: .jpg, .jpeg, .png, .bmp, .webp

## Name Resolution

- If photos are in subdirectories: Uses the directory name (e.g., `john/photo1.jpg` → "john")
- If photos are in the root: Uses the filename stem (e.g., `john_smith.jpg` → "john smith")

## Example Setup

```bash
# Create directories for people
mkdir -p data/faces/john
mkdir -p data/faces/jane

# Copy photos (one face per image)
cp /path/to/john_photo.jpg data/faces/john/
cp /path/to/jane_photo.jpg data/faces/jane/
```

## Testing

Run the demo to test recognition:

```bash
python demo_facial_recognition.py
```

## Tips for Best Results

- Use high-quality photos (at least 200x200 pixels)
- Ensure good lighting
- Avoid sunglasses or face coverings
- Multiple photos per person can improve accuracy
- Update photos occasionally as people's appearance changes
