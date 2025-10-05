# ReDustX

Asset Bundle repacker for Brown Dust 2 (Android). It finds the bundles that contain the assets your mods target, downloads only what’s needed, swaps the assets in-place, and writes the result to a separate output folder ready to copy to your phone. Includes a JSON → SKEL converter (beta) for Spine 4.1 JSON files.

If you want to request a feature or report a bug, please open an issue.

## Features

- Automatic bundle discovery (per quality: SD/HD/FHD)
- Only downloads the bundles actually needed by your mods
- Replaces the original assets with your modded assets
- ASTC encoding tuned per quality (HD = 4x4, SD = 8x8)
- JSON → SKEL Converter (beta) for Spine 4.1
- Duplicate mod detection and clear progress output
- Cross‑platform: available for both Windows and Linux

## Download

Download a prebuilt zip from the [Releases](https://github.com/Jelosus2/ReDustX/releases) page. Each archive contains what you need to run the program on that platform. Unzip anywhere, then proceed with the steps in the Quick Start section below.

Archives available:
- `ReDustX-win-x64.zip`  Windows 64‑bit (x86_64 / AMD64)
- `ReDustX-win-arm64.zip`  Windows on ARM 64‑bit
- `ReDustX-linux-x64.zip`  Linux 64‑bit (x86_64)
- `ReDustX-linux-arm64.zip`  Linux 64‑bit ARM (aarch64)

## Quick Start

### Windows
1. Put your mod files under `mods/` (see Folder Structure below).
2. Run `install.bat` to install the dependencies or `run.bat` if already installed.
3. In the menu, choose `Repack`, select your in‑game quality, and wait for completion.
4. Copy everything from `bundles_modded/` to your phone: `Android/data/com.neowizgames.game.browndust2/files/UnityCache/Shared/`.

### Linux
1. Ensure Python 3 is installed and the venv module is available.
2. Put your mod files under `mods/` (see Folder Structure below).
3. Run `./install.sh` to install the dependencies or `./run.sh` if already installed.
4. In the menu, choose `Repack`, select your in‑game quality, and wait for completion.
5. Copy everything from `bundles_modded/` to your phone: `Android/data/com.neowizgames.game.browndust2/files/UnityCache/Shared/`.

Note (Linux): ensure these files are executable if needed:
```
chmod +x astc_encoder/astcenc-sse2 # On x64 architecture
chmod +x astc_encoder/astcenc-neon # On ARM64 architecture
chmod +x run.sh
chmod +x install.sh
```

## Folder Structure

Place each mod in its own folder under `mods/`. File names must match the asset names inside the Unity bundles the game uses. A typical layout looks like this. Using Darian: Prophetic Dream assets as an example here:

```
mods/
|-- Darian_mod/
|   |-- char004001.skel      # Spine skeleton
|   |-- char004001.atlas     # Atlas text
|   |-- char004001.png       # Texture(s)
|   
|-- another_mod/
    |-- ...
```

Spine JSON exports are not repackable as‑is. If you only have JSON, use the built‑in `Json2Skel Converter (Beta)` first or ask the mod author for the `.skel` file.

## Troubleshooting

- No mods found
  - Ensure you follow the [folder structure](#folder-structure).
- Duplicate mods detected
  - Two different files resolve to the same target name. Remove duplicates and retry.
- Could not download catalog
  - Check your internet connection and try again later.
- ASTC encoder error
  - Windows: ensure `astc_encoder/astcenc-sse2.exe` or `astc_encoder/astcenc-neon.exe` exists.
  - Linux: ensure `astc_encoder/astcenc-sse2` or `astc_encoder/astcenc-neon` is present and executable (`chmod +x`).
- JSON → SKEL conversion fails
  - Only Spine 4.1 JSON is supported at the moment; if it is 4.1 and still fails, please open an issue or contact me on Discord: `Jelosus1`.
- “No matching bundle” for a file
  - The file name must exactly match the asset path stored in the bundle.

## Credits

This project is only possible thanks to these libraries and tools:
- [UnityPy](https://github.com/K0lb3/UnityPy) — Unity assets/bundle reader/writer
- [requests](https://docs.python-requests.org/) — HTTP client
- [protobuf](https://github.com/protocolbuffers/protobuf) — Protocol Buffers
- [Pillow](https://python-pillow.github.io/) — Image processing
- [InquirerPy](https://github.com/kazhala/InquirerPy) — Interactive CLI prompts
- [tqdm](https://github.com/tqdm/tqdm) — Progress bars
- [astcenc](https://github.com/ARM-software/astc-encoder) — ASTC Texture Compressor by Arm

Big thanks to Synae (BrownDustX author) as co‑author/collaborator on the project.

## Donations

If you like this tool and want to support the work:
- https://ko-fi.com/jelosus1
- https://ko-fi.com/synae

## Disclaimer

This software is provided “as is”, without warranty of any kind. Use at your own risk. ReDustX is not affiliated with NEOWIZ or PMANG.
