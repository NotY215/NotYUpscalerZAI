import cv2
import numpy as np
from .base_enhancer import BaseEnhancer

class ProDetailEnhancer(BaseEnhancer):
    def enhance_frame(self, frame):
        frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
        return super().enhance_frame(frame)

    def get_ffmpeg_vf(self, tw, th):
        vf = super().get_ffmpeg_vf(tw, th)
        return f"hqdn3d=4:4:3:3,unsharp=5:5:1.5,{vf}"