import cv2
from .base_enhancer import BaseEnhancer

class LiteRestoreEnhancer(BaseEnhancer):
    def enhance_frame(self, frame):
        frame = cv2.bilateralFilter(frame, 7, 35, 35)
        return super().enhance_frame(frame)

    def get_ffmpeg_vf(self, tw, th):
        vf = super().get_ffmpeg_vf(tw, th)
        return f"hqdn3d=3:3:2:2,{vf}"