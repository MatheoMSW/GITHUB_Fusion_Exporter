# Fusion 360 to GitHub Exporter

A Fusion 360 Python script that exports 3D models (`.step`, `.stl`, `.3mf`, `.f3d`), 2D PCBs (`.brd`, `.fbrd`), schematics (`.sch`, `.fsch`), and a `VERSION.txt` manifest directly into your local GitHub repository folder and opens GitHub Desktop.

## 🚀 Easy Installation (2 Minutes)

### Step 1: Download the Code
1. Click the green **`<> Code`** button at the top of this page.
2. Select **Download ZIP** and extract the downloaded archive.

### Step 2: Copy into Fusion 360's Scripts Folder
Copy the **`GitHubExporter`** folder (containing `GitHubExporter.py` and `GitHubExporter.manifest`) into your Fusion 360 Scripts directory:

* **Windows:**
  ```text
  %appdata%\Autodesk\Autodesk Fusion 360\API\Scripts\
  ```
  *(Paste that path into the Windows File Explorer address bar and press Enter.)*

* **macOS:**
  ```text
  ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/
  ```

### Step 3: Run in Fusion 360
1. Open **Fusion 360** and press **`Shift + S`** (or go to **Utilities > Add-Ins > Scripts and Add-Ins**).
2. Under **My Scripts**, select **`GitHubExporter`**.
3. Click **Run**.
