# NotYUpscalerZAI

<p align="center">
  <img src="https://iili.io/q9ls4O7.jpg" alt="NotYUpscalerZAI Logo" width="140">
</p>

<h3 align="center">
  Near-Topaz Quality Upscaler & Enhancer – Optimized for Low/Mid-End PCs
</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/OpenCV-4.10+-green?style=for-the-badge&logo=opencv">
  <img src="https://img.shields.io/badge/CustomTkinter-5.2+-orange?style=for-the-badge">
  <img src="https://img.shields.io/badge/FFmpeg-bundled-brightgreen?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-GPL%203.0-red?style=for-the-badge&logo=gnu">
</p>

<p align="center">
  <b>Professional local image & video enhancement • 4 GB RAM minimum • Aspect ratio preserved • No internet required</b>
</p>

<p align="center">
  <a href="https://github.com/NotY215/NotYUpscalerZAI/releases/latest">
    <img src="https://img.shields.io/badge/Download%20Latest%20Release-blue?style=for-the-badge&logo=github">
  </a>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Requirements](#-system-requirements)
- [Quality + Speed Notes](#quality--speed-notes)
- [Key Features](#-key-features)
- [Download & Installation](#-download--installation)
- [License](#-license)

---

## 🎯 Overview

**NotYUpscalerZAI** is a free, open-source desktop tool that delivers high-quality image and video enhancement/upscaling on modest hardware — bringing results close to paid tools like Topaz, but running smoothly on low-end laptops and desktops.

It combines:

- High-quality Lanczos resizing
- Adaptive sharpening (unsharp mask)
- Edge enhancement & detail recovery
- Light denoising (hqdn3d / fastNlMeans)
- Contrast, saturation & subtle glow adjustments

Everything runs **locally** — no cloud processing, no subscriptions, no heavy deep learning models.

Ideal for:
- Budget laptops (i3 dual/quad-core, 4–16 GB RAM)
- Integrated graphics (Intel UHD/HD, AMD Radeon)
- Older discrete GPUs (GT 610, GT 730, GTX series entry-level)

---

## 💻 System Requirements

### Minimum (Runs acceptably)
| Component       | Requirement                          |
|-----------------|--------------------------------------|
| **CPU**         | Intel Core i3 Dual-Core or equivalent |
| **RAM**         | 4 GB                                 |
| **GPU**         | Integrated graphics                  |
| **OS**          | Windows 10/11 (64-bit)               |
| **Storage**     | ~800 MB – 1.2 GB free                |

### Recommended (Smooth & best quality)
| Component       | Recommendation                       |
|-----------------|--------------------------------------|
| **CPU**         | Intel Core i5 Quad-Core or better    |
| **RAM**         | 8–16 GB                              |
| **GPU**         | NVIDIA GT 610 / GT 730 or equivalent |
| **OS**          | Windows 11 (64-bit)                  |

---

## Quality + Speed Notes

| Scenario                              | Quality Level          | Processing Speed / File Size | Recommendation                          |
|---------------------------------------|------------------------|-------------------------------|-----------------------------------------|
| Single pass (recommended)             | Best balance           | Good                          | Most users – clean, natural results     |
| Very high sharpen on live preview     | Can look over-sharpened / bright | Instant preview               | Adjust carefully (see disclaimer below) |
| Export with high bitrate + slow preset| Highest detail retention | Slower, larger files          | Final archival / high-quality delivery  |
| Low bitrate + fast preset             | Good for web/social    | Very fast, smaller files      | Quick sharing / storage saving          |

---

## ✨ Key Features

### Image Enhancement/Upscaling
- Targets: Fit 2K, Fit 3K, Fit 4K (always preserves original aspect ratio)
- Models: Image Enhance (optimized denoising + subtle detail boost)
- Formats: JPG, PNG, WEBP, BMP, etc.
- Multi-step pipeline: Denoise → Bilateral filter → Contrast → Light edge enhancement

### Video Enhancement/Upscaling
- Upscale resolution + quality boost (no frame rate change)
- Models: Lite Restore • Pro Detail • Ultra Native (different denoising & detail strategies)
- Sharpen strength slider (affects export filter strength)
- Bitrate control: 4–60 Mbps with real-time size estimation
- Auto FFmpeg preset (veryfast → slow) based on chosen bitrate
- Supported inputs/outputs: MP4, MKV, AVI, MOV + more via FFmpeg
- Live preview + timeline scrubbing

### Interface Highlights
- Dark modern theme with cyan/neon accents
- Side-by-side Original vs Enhanced preview (680×460)
- Video timeline + Play/Pause + Open in default player
- Real-time progress bar & cancel during long exports
- Estimated output file size display
- Output folder selection

### Performance
- Designed for 4 GB RAM machines
- Export runs in background (UI remains responsive)
- Bundled FFmpeg → no separate installation
- GPL-3.0 open source – free to use/modify

---

## 📥 Download & Installation

**Latest release**  
→ https://github.com/NotY215/NotYUpscalerZAI/releases/latest

1. Download the standalone `.exe` (~200-300 MB)
2. Run the executable (no install needed)
3. Accept GPL-3.0 terms on first launch
4. Select image/video → choose model/resolution/settings → Export

**Antivirus note**: Some scanners flag PyInstaller bundles as false positives. Add an exception or build from source if needed.

---
# ⚖️ License
Released under the GNU General Public License v3.0
→ See the LICENSE file for full terms.
You may use, modify, and redistribute — provided derivatives remain open-source under GPL-3.0.

Made with ❤️ for the community by NotY215
Last updated: March 2026