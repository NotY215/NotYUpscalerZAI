import os
import cv2
import torch
import numpy as np
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
from gfpgan import GFPGANer
import urllib.request

class RealESRGANEnhancer:
    def __init__(self, device="cpu"):
        self.device = device
        self.model_path = "models/RealESRGAN_x4plus.pth"
        self.gfpgan_path = "models/GFPGANv1.4.pth"
        self.download_weights()
        self.load_models()

    def download_weights(self):
        os.makedirs("models", exist_ok=True)
        urls = {
            self.model_path: "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
            self.gfpgan_path: "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"
        }
        for path, url in urls.items():
            if not os.path.exists(path):
                print(f"Downloading {os.path.basename(path)} ...")
                urllib.request.urlretrieve(url, path)
                print(f"Downloaded {os.path.basename(path)}")

    def load_models(self):
        # Real-ESRGAN
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        self.upsampler = RealESRGANer(
            scale=4,
            model_path=self.model_path,
            model=model,
            tile=400,
            tile_pad=10,
            pre_pad=0,
            half=False,
            device=torch.device(self.device)
        )

        # GFPGAN for faces
        self.gfpgan = GFPGANer(
            model_path=self.gfpgan_path,
            upscale=4,
            arch='clean',
            channel_multiplier=2,
            bg_upsampler=self.upsampler,
            device=torch.device(self.device)
        )

    def enhance_image(self, img_bgr, face_restore=True):
        img = img_bgr.copy()
        # Denoise before AI
        img = cv2.fastNlMeansDenoisingColored(img, None, 8, 8, 7, 21)

        if face_restore:
            _, _, output = self.gfpgan.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
            output = cv2.convertScaleAbs(output, alpha=1.05, beta=5)  # slight contrast boost
            return output
        else:
            output, _ = self.upsampler.enhance(img, outscale=4)
            return output