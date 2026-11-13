# Fusion 360 to GitHub Exporter

A Python toolset for **Autodesk Fusion 360** that exports your 3D CAD models, 3D PCBs, 2D PCBs, and schematics directly into a local Git repository folder—ready to commit and push via **GitHub Desktop**.

Choose between two versions depending on your workflow:
1. **Add-In (`Github Exporter`) — Recommended:** Runs in the background, exports automatically every time you save (`Ctrl + S`), and adds quick-access buttons right next to the **Save** icon in the top bar.
2. **Script (`GitHubExporter`) — Manual:** Runs on demand whenever you want to export your open tabs in one click.

---

## ✨ Features

* **Auto-Export on Save (Add-In):** Silently updates your repository folder whenever you press `Ctrl + S` (`Cmd + S` on Mac).
* **Top-Bar Controls (Add-In):**
  * **Green / Red Square (Next to Save):** Toggle automatic export on save **ON** or **OFF**.
  * **Blue Square (Next to Save):** Trigger an immediate manual export (**GitHub Export Now**).
  * **GitHub Export Folder... (`Utilities > Add-Ins`):** Switch your target local repository folder anytime.
* **Multi-Format 3D & Electronics Support:**
  * **3D CAD & 3D PCB:** `.step`, `.stl` (for interactive 3D browser previews on GitHub), `.3mf`, and native `.f3d`.
  * **2D Electronics:** `.brd` / `.fbrd` (2D PCB layout) and `.sch` / `.fsch` (schematic).
* **Automatic `VERSION.txt` Manifest:** Records the Fusion 360 version number (e.g., `v14`), export timestamp, and a description of every exported file.

---

## 📦 Repository Structure

```text
Fusion360-GitHub-Exporter/
├── AddIn/
│   └── Github Exporter Save/             <-- Copy into Fusion 360's AddIns folder
│       ├── Github Exporter.py
│       └── Github Exporter.manifest
├── Script/
│   └── GitHubExporter/              <-- Copy into Fusion 360's Scripts folder
│       ├── GitHubExporter.py
│       └── GitHubExporter.manifest
└── README.md
```

---

## 🚀 Installation

### Option 1: Install the Add-In (Recommended)

1. **Download:** Click the green **`<> Code`** button at the top of this page, select **Download ZIP**, and extract it.
2. **Copy Folder:** Move the **`Github Exporter Save`** folder into your Fusion 360 **AddIns** directory:
   * **Windows:**
     ```text
     %appdata%\Autodesk\Autodesk Fusion 360\API\AddIns\
     ```
   * **macOS:**
     ```text
     ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/
     ```
3. **Activate in Fusion 360:**
   * Open Fusion 360 and press **`Shift + S`** (or go to **Utilities > Add-Ins > Scripts and Add-Ins**).
   * Switch to the **Add-Ins** tab at the top.
   * Select **`Github Exporter`**, check **Run on Startup**, and click **Run**.
   * Select your local cloned **GitHub repository folder** when prompted.

---

### Option 2: Install the Manual Script

1. **Copy Folder:** Move the **`GitHubExporter`** folder into your Fusion 360 **Scripts** directory:
   * **Windows:**
     ```text
     %appdata%\Autodesk\Autodesk Fusion 360\API\Scripts\
     ```
   * **macOS:**
     ```text
     ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/
     ```
2. **Run in Fusion 360:**
   * Open Fusion 360 and press **`Shift + S`**.
   * Under **My Scripts**, select **`GitHubExporter`** and click **Run**.
   * Choose your target GitHub folder and confirm the project subfolder name.

---

## 🛠️ Daily Workflow

1. **Design & Save:** Work normally in Fusion 360 and press **`Ctrl + S`** (with the Add-In active) or click the **Blue Export Now** button in the top bar.
2. **Review Changes:** Open **GitHub Desktop**—your updated 3D files, PCB files, and `VERSION.txt` appear automatically.
3. **Commit & Push:** Write a short commit summary, click **Commit to main**, and click **Push origin**.



> [!WARNING]
> This is a Beta Version, there could be Bugs.
