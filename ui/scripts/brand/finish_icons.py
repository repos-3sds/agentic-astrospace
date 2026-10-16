"""Second step after render-icons.cjs: flatten what must be opaque (the iOS
icon is rejected with an alpha channel) and write the web formats. Run from ui/."""
import glob
import os
import tempfile

from PIL import Image

OUT = os.path.join(tempfile.gettempdir(), 'siddha-icons')
R = 'android/app/src/main/res/'
opaque = (
    ['assets/icon.png']
    + glob.glob('ios/App/App/Assets.xcassets/AppIcon*.appiconset/*.png')
    + glob.glob(R + 'mipmap-*/ic_launcher*_background.png')
)
for f in opaque:
    Image.open(f).convert('RGB').save(f, optimize=True)
for s in (48, 72, 96, 128, 192, 256, 512):
    Image.open(f'{OUT}/icon-{s}.png').convert('RGB').save(f'icons/icon-{s}.webp', quality=92)
Image.open(f'{OUT}/fav-256.png').convert('RGBA').save('public/favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
