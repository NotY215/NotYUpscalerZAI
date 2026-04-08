import cv2
import numpy as np
from .base_enhancer import BaseEnhancer

class ImageEnhanceModel(BaseEnhancer):
    def __init__(self, **kwargs):
        super().__init__(contrast=1.18, saturation=1.22, glow=0.0, **kwargs)

    def enhance_frame(self, frame):
        if frame is None or frame.size == 0:
            return frame

        frame = cv2.bilateralFilter(frame, d=7, sigmaColor=45, sigmaSpace=45)

        try:
            frame = cv2.fastNlMeansDenoisingColored(frame, None, h=6, hColor=6, templateWindowSize=5, searchWindowSize=11)
        except:
            pass

        frame = cv2.convertScaleAbs(frame, alpha=self.contrast, beta=0)

        blurred = cv2.GaussianBlur(frame, (0,0), 1.8)
        frame = cv2.addWeighted(frame, 1.25, blurred, -0.25, 0)

        if self.glow > 0:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return frame

    def get_ffmpeg_vf(self, tw, th):
        return f"scale={tw}:{th}:flags=lanczos"