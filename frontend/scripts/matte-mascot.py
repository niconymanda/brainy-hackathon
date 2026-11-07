# Removes the uniform cream background (249,244,232) from a mascot frame, keeping soft glows.
# Usage: python3 matte-mascot.py in.png out.png  (needs numpy, opencv-python-headless, scipy)
import sys, numpy as np, cv2
from scipy.ndimage import binary_fill_holes
B = np.array([249,244,232], np.float32)
def matte(path):
    C = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(np.float32)
    d = C - B
    noise = 3.0
    dark = np.clip((-d - noise) / (B - noise), 0, 1)
    light = np.clip((d - noise) / (255 - B + 20), 0, 1)
    a_min = np.maximum(dark, light).max(2)
    r,g,b = C[...,0],C[...,1],C[...,2]
    body = (b - r > 50) & (b > 110)
    body = cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5,5),np.uint8)).astype(bool)
    body = binary_fill_holes(body)
    body = cv2.GaussianBlur(body.astype(np.float32), (0,0), 1.2)
    a = np.maximum(a_min, body)
    a = cv2.GaussianBlur(a, (0,0), 0.6)
    a3 = a[...,None]
    F = np.where(a3 > 1e-3, (C - (1 - a3) * B) / np.maximum(a3, 1e-3), 0)
    F = np.clip(F, 0, 255)
    return np.dstack([F, a*255]).astype(np.uint8)
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    out = matte(src)
    cv2.imwrite(dst, cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
