import cv2
import numpy as np
from .base_enhancer import BaseEnhancer

class ImageEnhanceModel(BaseEnhancer):
    def __init__(self, **kwargs):
        # No sharpen parameter needed anymore for pure image enhancement
        super().__init__(contrast=1.18, saturation=1.22, glow=0.0, **kwargs)

    def enhance_frame(self, frame):
        if frame is None or frame.size == 0:
            return frame

        # Light bilateral filter to reduce noise without losing detail
        frame = cv2.bilateralFilter(frame, d=7, sigmaColor=45, sigmaSpace=45)

        # Subtle denoising (very light to keep natural look)
        try:
            frame = cv2.fastNlMeansDenoisingColored(frame, None, h=6, hColor=6, templateWindowSize=5, searchWindowSize=11)
        except:
            pass

        # Apply contrast and saturation from base (controlled values)
        frame = cv2.convertScaleAbs(frame, alpha=self.contrast, beta=0)

        # Very subtle unsharp mask for edge clarity (no glow/brightness explosion)
        blurred = cv2.GaussianBlur(frame, (0,0), 1.8)
        frame = cv2.addWeighted(frame, 1.25, blurred, -0.25, 0)

        # Optional very light glow/highlight recovery (disabled by default)
        if self.glow > 0:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return frame

    def get_ffmpeg_vf(self, tw, th):
        # For images we don't use FFmpeg, but keep method for consistency
        return f"scale={tw}:{th}:flags=lanczos"