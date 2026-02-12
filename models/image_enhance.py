import cv2
import numpy as np
from .base_enhancer import BaseEnhancer

class ImageEnhanceModel(BaseEnhancer):
    def enhance_frame(self, frame):
        if frame is None or frame.size == 0:
            return frame

        frame = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
        try:
            frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
        except:
            pass

        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]], dtype=np.float32)
        frame = cv2.filter2D(frame, -1, kernel)

        return super().enhance_frame(frame)

    def get_ffmpeg_vf(self, tw, th):
        return f"scale={tw}:{th}:flags=lanczos,unsharp=5:5:1.5"