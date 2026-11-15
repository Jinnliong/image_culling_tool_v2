# image_culling_tool_v2

# 🦛 Project Hippocampus: The Documentary Curator Engine

*An AI-Powered Culling & Aesthetic Triage System for Visual Storytellers*

## 🏛️ Executive Summary

**Project Hippocampus** is an advanced, local-first image culling and curation suite designed specifically for documentary photographers, street shooters, and visual journalists. Named after the brain's center for memory and emotional consolidation, this software acts as an intelligent digital assistant—combining rigorous technical evaluation with nuanced aesthetic, narrative, and satirical judgement.

Powered by a lightweight vision-language model (`llava-phi3`) running locally via Ollama and orchestrated through a high-performance Streamlit dashboard, Hippocampus bridges the gap between cold mechanical image stats (sharpness, exposure, framing) and the human soul of photography (story, mood, and *Mo Lei Tou* absurdity).

## 🛠️ Installation & Setup (Bash Commands)

To set up your local environment, install the required system software, Python libraries, and pull the vision model, run the following commands in your terminal:

```bash
# 1. Install Ollama (for macOS / Linux / Windows WSL)
# Visit https://ollama.com for direct installers, or use curl on Linux/macOS:
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull the lightweight vision model required by Project Hippocampus
ollama pull llava-phi3

# 3. Clone or navigate to your project directory
cd /path/to/image_culling_tool

# 4. Create and activate a virtual environment (Recommended)
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# 5. Install the required Python libraries
pip install streamlit pandas psutil ollama pillow requests torch
```

## ⚙️ Core Architecture & Codebase

The system is engineered as a clean, modular Python application consisting of three core pillars:

1. **`app.py` (The Control Deck):** A reactive Streamlit interface managing real-time system health (CPU/RAM telemetry), live scan loops, 10-frame champion broadcasts, and a zero-lock dual-pane interactive inspector with keyboard shortcuts.

2. **`ai_engine.py` (The Vision Jury):** Evaluates images against 5W+1H journalistic standards, visual layering, and subversion metrics, outputting granular, non-rounded intelligence scores.

3. **`utils.py` (The Scout & Transmitter):** Handles EXIF metadata extraction (focal length, aperture), smart in-memory image compression, persistent settings management, and live Telegram integrations.

## 🌟 Key Features & Capabilities

### 1. The Composition-First Triage Engine

Unlike traditional culling software that relies solely on simple burst-detection or basic sharpness algorithms, Hippocampus uses a **Composition-First Hierarchy (45% weight on framing)** to route photos into intelligent categories:

* **🌟 Keeper Masterpiece:** Flawless convergence of framing, documentary story, emotional mood, and technical execution.

* **📖 Keeper Storyteller:** High narrative depth and human presence.

* **🎭 Keeper Mood:** Strong chiaroscuro, lighting quality, and visceral atmosphere.

* **⚡ Keeper Maverick & Mo Lei Tou:** Captures street irony, visual collisions, and deadpan absurdity in the spirit of classic visual subversion.

* **⚙️ Keeper Technical / Review / Discard:** Safe fallback tiers and hard discards for severe technical failure.

### 2. The 10-Frame Champion Spotlight & Telegram Sync

During live scans, the engine batches photos into rolling 10-frame windows. It automatically calculates a composite documentary score balancing technical execution with soul and story, crowns a **Batch Champion**, displays it in an immersive live UI container, and instantly transmits a formatted telemetry card directly to Telegram.

### 3. Zero-Lock Interactive Inspector

Equipped with live arrow-key navigation (`←` / `→`), the inspector allows photographers to breeze through thousands of culling candidates with zero interface lag. It features dynamic thumbnail downscaling, auto-orientation via EXIF headers, and full display of the AI curator's written critique and roast scores.

### 4. Physical Deploy Router

Once the review session is complete, a single click triggers a physical file re-routing protocol—organizing your raw directory into clean subfolders (`1_Masterpiece`, `2_Storyteller`, `3_Mood`, `4_Technical`, `5_Maverick`, `Review_Needed`, and `Discarded`) without breaking a sweat.

## 🚀 System Philosophy: Why Hippocampus?

For the serious documentary photographer, sorting through thousands of frames after a grueling shoot is exhausting. Traditional software treats photography as a spreadsheet problem. **Project Hippocampus treats photography as art.**

By running entirely locally, your private archives remain completely secure, your computer's memory is aggressively managed to prevent hardware bottlenecks, and your unique creative standards are respected, synced, and celebrated.
