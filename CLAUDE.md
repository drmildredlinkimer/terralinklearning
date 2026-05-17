# TerraLink Learning — Project Notes

## File Conversion: MarkItDown

**MarkItDown 0.1.5** (Microsoft) is installed at `/usr/local/bin/markitdown`.

Whenever the user asks to convert or read any of the following file types, run `markitdown <file>` first to convert it to Markdown, then read the resulting Markdown:

- PDF (`.pdf`)
- Word (`.docx`, `.doc`)
- Excel (`.xlsx`, `.xls`)
- PowerPoint (`.pptx`, `.ppt`)
- Images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`)
- Audio (`.mp3`, `.wav`, `.m4a`, `.ogg`)
- Video (`.mp4`, `.mov`, `.avi`, `.mkv`)
- HTML (`.html`, `.htm`)
- CSV (`.csv`)
- ZIP archives (`.zip`)

### Usage

```bash
# Convert and capture output
markitdown archivo.pdf

# Convert to a .md file
markitdown archivo.pdf -o archivo.md
```

Trigger phrases include: "convierte", "lee este archivo", "convert", "read this file", "analiza este documento", and similar.
