import cv2
from .base_enhancer import BaseEnhancer

class LiteRestoreEnhancer(BaseEnhancer):
    def __init__(self, sharpen=1.8, **kwargs):
        super().__init__(sharpen=sharpen, **kwargs)

    def enhance_frame(self, frame):
        frame = cv2.bilateralFilter(frame, 7, 35, 35)
        return super().enhance_frame(frame)

    def get_ffmpeg_vf(self, tw, th):
        vf = super().get_ffmpeg_vf(tw, th)
        return f"hqdn3d=3:3:2:2,{vf}"