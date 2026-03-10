# NotYUpscalerZAI

<p align="center">
  <img src="https://iili.io/q9ls4O7.jpg" alt="NotYUpscalerZAI Logo" width="140">
</p>

<h3 align="center">
  Topaz-Level Quality Upscaler – Runs Perfectly on Low/Mid-End PCs
</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/OpenCV-4.13+-green?style=for-the-badge&logo=opencv">
  <img src="https://img.shields.io/badge/CustomTkinter-5.2+-orange?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-GPL%203.0-red?style=for-the-badge&logo=gnu">
  <img src="https://img.shields.io/github/v/release/NotY215/NotYUpscalerZAI?color=brightgreen&style=for-the-badge">
</p>

<p align="center">
  <b>Professional-grade image & video upscaling • 4 GB RAM minimum • Preserves aspect ratio • No cloud needed</b>
</p>

<p align="center">
  <a href="https://github.com/NotY215/NotYUpscalerZAI/releases/latest">
    <img src="https://img.shields.io/badge/Download%20Latest%20Release-blue?style=for-the-badge&logo=github">
  </a>
</p>

---

## 📋 Table of Contents

#### - [Overview](#-overview)
#### - [System Requirements](#-system-requirements)
#### - [QUALITY + SPEED ](#quality--speed)
#### - [Key Features](#-Key-Features)
#### - [Download & Installation](#-download--installation)
#### - [License](#-license)


---

## 🎯 Overview

**NotYUpscalerZAI v6.2** is a free, open-source desktop application that brings **near-Topaz quality upscaling** to low-end and mid-range PCs — without needing powerful GPUs, cloud subscriptions, or 32 GB RAM.

It uses a carefully tuned combination of:

- Lanczos scaling
- Adaptive unsharp masking
- Edge-aware sharpening
- Light denoising
- Contrast & saturation enhancement

All processing is done **locally** on your machine. No internet required after download.

Perfect for:
- Old laptops (i3/i5 4th–8th gen, 4–16 GB RAM)
- Integrated graphics (Intel HD/UHD, AMD Radeon)
- Entry-level dedicated GPUs (GT 610, GT 730, GTX 750)

---

## 💻 System Requirements

### Minimum (Works smoothly)
| Component       | Requirement                  |
|-----------------|------------------------------|
| **CPU**         | Intel Core i3 Dual-Core or equivalent |
| **RAM**         | 4 GB DDR3/DDR4               |
| **GPU**         | Integrated (Intel HD / AMD Radeon) |
| **OS**          | Windows 10/11 (64-bit)       |
| **Storage**     | ~1 GB free                 |
| **Python**      | Not needed (standalone .exe) |

### Recommended (Best quality & speed)
| Component       | Requirement                  |
|-----------------|------------------------------|
| **CPU**         | Intel Core i5 Quad-Core or better |
| **RAM**         | 8–16 GB                      |
| **GPU**         | NVIDIA GT 610 / GT 730 or better |
| **OS**          | Windows 11 (64-bit)          |

---


## Quality + Speed

| Order | Quality (noise / artifacts) | Speed / Workflow efficiency | When to use it anyway |
|------|-------------------------------|------------------------------|-----------------------|
| Edit → Export → Enhance | **Best – cleanest result** | Very good (most common pro workflow) | Almost all serious projects |
| Enhance first → then edit in AE | **Worst – noise/artifacts amplified** | Slightly faster editing (smaller files) | Only very quick social media / low-budget jobs |
| Enhance → Export → Re-enhance (double pass) | **Extremely bad – compounding artifacts** | Waste of time | Never do this |

---
## ✨ Key Features

### Image Upscaling
- Targets: Fit 2K / Fit 3K / Fit 4K (preserves original aspect ratio)
- Multi-stage enhancement: Denoise → Sharpen → Contrast → Glow
- Supports JPG, PNG, WEBP, BMP

### Video Upscaling
- Resolution upscale + quality boost (no FPS change)
- Bitrate control: 4–60 Mbps slider (higher = better quality, larger file)
- Auto-preset selection based on bitrate (veryfast → slow)
- Supports MP4, MKV, AVI, MOV input/output
- Live preview with real-time sharpening

### User Interface
- Modern dark theme with cyan accents
- Side-by-side original vs enhanced preview
- Timeline scrubbing for videos
- Play/Pause + Open in default player
- Progress bar + cancel button during export
- Real-time estimated output file size display

### Performance
- Optimized for low RAM & weak CPUs
- Background export (UI stays responsive)
- No internet or cloud needed
- GPL-3.0 open source – free forever

---

## 📥 Download & Installation

**Latest stable release (v6.2)**  
→ https://github.com/NotY215/NotYUpscalerZAI/releases/latest

1. Download the `.exe` file (around 700-800 MB standalone)
2. Run it (no installation needed)
3. Accept the GPL-3.0 license terms
4. Select media → adjust settings → Export

**That's it!** No Python or FFmpeg installation required — everything is bundled.

If any antivirus flags it (false positive common with PyInstaller exes), add exception or compile from source.

---

## ⚖️ License

This project is licensed under the **GNU General Public License v3.0**  
→ Full license text: [LICENSE](./LICENSE)

You are free to use, modify, and distribute — as long as derivative works remain open-source under GPL-3.0.

---

Made with ❤️ for the community by **NotY215**  
Last updated: March 2026
