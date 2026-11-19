"""Export the supplied Fig. 1 raster without redrawing its contents."""
from pathlib import Path
import os
import shutil
from PIL import Image

HERE = Path(__file__).resolve().parent

def main():
    source = HERE / "source" / "Fig1_supplied.png"
    root = os.environ.get("FIGURE_OUTPUT_ROOT")
    out = Path(root).expanduser().resolve() / "Fig1" if root else HERE / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, out / "Fig1.png")
    # PDF pages are opaque. Preserve transparent source pixels against the
    # same white background used by the manuscript, rather than dropping alpha.
    supplied = Image.open(source).convert("RGBA")
    image = Image.new("RGB", supplied.size, "white")
    image.paste(supplied, mask=supplied.getchannel("A"))
    image.save(out / "Fig1.pdf", "PDF", resolution=300.0)

if __name__ == "__main__":
    main()
