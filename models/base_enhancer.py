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

        # Safe denoise
        try:
            frame = cv2.fastNlMeansDenoisingColored(frame, None, 8, 8, 7, 21)
        except Exception as e:
            print("Denoise skipped:", e)

        # Contrast & Saturation - safe LAB
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=self.contrast * 3, tileGridSize=(8,8))
            l = clahe.apply(l)
            # Resize channels to match L if needed
            if a.shape != l.shape:
                a = cv2.resize(a, (l.shape[1], l.shape[0]))
            if b.shape != l.shape:
                b = cv2.resize(b, (l.shape[1], l.shape[0]))
            lab = cv2.merge([l, a * self.saturation, b * self.saturation])
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        except Exception as e:
            print("LAB skipped:", e)

        # Sharpen
        kernel = np.array([[-1,-1,-1], [-1, 1 + self.sharpen*8, -1], [-1,-1,-1]]) / (self.sharpen*8 + 1)
        frame = cv2.filter2D(frame, -1, kernel)

        # Glow
        if self.glow > 0:
            blurred = cv2.GaussianBlur(frame, (0,0), 18)
            frame = cv2.addWeighted(frame, 1.0, blurred, self.glow*0.8, 0)

        return frame

    def get_ffmpeg_vf(self, tw, th):
        return (f"scale={tw}:{th}:flags=lanczos,unsharp=5:5:{self.sharpen*1.2},"
                f"eq=contrast={self.contrast}:saturation={self.saturation}")