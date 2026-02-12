import cv2
import numpy as np
from .base_enhancer import BaseEnhancer

class UltraNativeEnhancer(BaseEnhancer):
    def enhance_frame(self, frame):
        frame = cv2.fastNlMeansDenoisingColored(frame, None, 12, 12, 7, 25)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Laplacian(gray, cv2.CV_64F)
        edges = cv2.convertScaleAbs(edges)
        edges = cv2.GaussianBlur(edges, (0,0), 1.5)
        frame = cv2.addWeighted(frame, 1.0, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), 0.55, 0)
        return super().enhance_frame(frame)

    def get_ffmpeg_vf(self, tw, th):
        vf = super().get_ffmpeg_vf(tw, th)
        return f"cas=0.95,hqdn3d=5:5:4:4,unsharp=7:7:2.5,{vf}"