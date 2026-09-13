"""Build ICNS sizes and an original monochrome menu glyph using AppKit."""
from pathlib import Path
import subprocess
from AppKit import NSImage, NSBezierPath, NSColor, NSBitmapImageRep, NSPNGFileType, NSCompositingOperationCopy, NSRectFillUsingOperation

root = Path(__file__).resolve().parent
iconset = root / 'AppIcon.iconset'
iconset.mkdir(exist_ok=True)
for size in (16, 32, 128, 256, 512):
    for scale in (1, 2):
        target = iconset / f'icon_{size}x{size}{"@2x" if scale == 2 else ""}.png'
        subprocess.run(['/usr/bin/sips', '-z', str(size * scale), str(size * scale), str(root / 'AppIcon-original.png'), '--out', str(target)], check=True, stdout=subprocess.DEVNULL)
if not (root / 'AppIcon.icns').exists():
    subprocess.run(['/usr/bin/iconutil', '-c', 'icns', str(iconset), '-o', str(root / 'AppIcon.icns')], check=True)
# Original 18-point template glyph; no system symbol artwork is redistributed.
image = NSImage.alloc().initWithSize_((36, 36))
image.lockFocus()
NSColor.blackColor().set()
for rect, radius in [(((4, 10), (28, 16)), 3), (((10, 24), (16, 8)), 1), (((10, 3), (16, 12)), 1)]:
    NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, radius, radius).fill()
NSColor.clearColor().set()
NSRectFillUsingOperation(((13, 7), (10, 2)), NSCompositingOperationCopy)
NSRectFillUsingOperation(((13, 11), (10, 2)), NSCompositingOperationCopy)
image.unlockFocus()
rep = NSBitmapImageRep.imageRepWithData_(image.TIFFRepresentation())
rep.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(str(root / 'MenuBar.png'), True)
