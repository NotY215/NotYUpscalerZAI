# models/image_enhance.py
import cv2
import numpy as np

class ImageEnhanceModel:
    def __init__(self):
        # No parameters needed anymore — pure natural enhancement
        pass

    def enhance_frame(self, frame):
        """
        Pure, natural-looking image enhancement:
        - Gentle noise reduction (bilateral filter)
        - Mild contrast & brightness boost
        - Subtle edge/detail enhancement (Laplacian)
        - No aggressive sharpening → avoids glow/dull issues
        """
        if frame is None or frame.size == 0:
            return frame

        try:
            # Step 1: Gentle denoising + detail preservation
            frame = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)

            # Step 2: Mild contrast & saturation/brightness boost
            frame = cv2.convertScaleAbs(frame, alpha=1.12, beta=8)

            # Step 3: Subtle edge/detail enhancement (natural look)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Laplacian(gray, cv2.CV_64F)
            edges = cv2.convertScaleAbs(edges)
            edges = cv2.GaussianBlur(edges, (0, 0), 1.2)  # slight softening
            frame = cv2.addWeighted(frame, 1.0, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), 0.28, 0)

            return frame

        except Exception as e:
            print("Image enhancement error:", str(e))
            return frame

    def get_ffmpeg_vf(self, tw, th):
        """
        For video consistency — very light processing only
        (no heavy filters to avoid FFmpeg errors)
        """
        return f"scale={tw}:{th}:flags=lanczos"