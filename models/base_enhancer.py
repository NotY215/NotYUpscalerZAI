import cv2
import numpy as np

class BaseEnhancer:
    def __init__(self, sharpen=1.8, contrast=1.25, saturation=1.15, glow=0.4):
        self.sharpen = sharpen
        self.contrast = contrast
        self.saturation = saturation
        self.glow = glow

    def enhance_frame(self, frame):
        if frame is None or frame.size == 0:
            return frame

        # Denoise
        try:
            frame = cv2.fastNlMeansDenoisingColored(frame, None, 8, 8, 7, 21)
        except:
            pass

        # Simple contrast
        try:
            frame = cv2.convertScaleAbs(frame, alpha=self.contrast, beta=0)
        except:
            pass

        # Sharpen
        kernel = np.array([[-1,-1,-1], [-1, 1 + self.sharpen*9, -1], [-1,-1,-1]], dtype=np.float32) / (self.sharpen*9 + 1)
        frame = cv2.filter2D(frame, -1, kernel)

        # Glow
        if self.glow > 0:
            blurred = cv2.GaussianBlur(frame, (0,0), 18)
            frame = cv2.addWeighted(frame, 1.0, blurred, self.glow*0.8, 0)

        return frame

    def get_ffmpeg_vf(self, tw, th):
        return (f"scale={tw}:{th}:flags=lanczos,unsharp=7:7:{self.sharpen*1.8},"
                f"cas=0.9,eq=contrast={self.contrast}:saturation={self.saturation}")