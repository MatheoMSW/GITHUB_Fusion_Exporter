import adsk.core
import adsk.fusion
import traceback
import os
import re
import time
import shutil
import subprocess
from datetime import datetime


def clean_name(raw_name):
    no_version = re.sub(r"\s+v\d+$", "", raw_name.strip())
    cleaned = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in no_version)
    return cleaned.strip("_") or "Fusion_Export"


def get_version_string(doc):
    """Gets version number from cloud dataFile or falls back to document title (e.g. 'v14')."""
    try:
        if doc.dataFile and doc.dataFile.versionNumber:
            return f"v{doc.dataFile.versionNumber}"
    except Exception:
        pass

    match = re.search(r"\b(v\d+)\b", doc.name.strip())
    if match:
        return match.group(1)

    return "Local Draft (Unsaved)"


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        active_doc = app.activeDocument
        if not active_doc:
            ui.messageBox("Open a Fusion 360 design first.")
            return

        # 1. Pick target repo folder
        folder_dlg = ui.createFolderDialog()
        folder_dlg.title = "Select Your Local GitHub Repository Folder"
        if folder_dlg.showDialog() != adsk.core.DialogResults.DialogOK:
            return
        repo_path = folder_dlg.folder

        # 2. Pick subfolder name
        default_proj = clean_name(active_doc.name)
        (proj_input, cancelled) = ui.inputBox(
            "Enter project subfolder name:", "GitHub Export", default_proj
        )
        if cancelled or not proj_input.strip():
            return

        export_dir = os.path.join(repo_path, clean_name(proj_input))
        os.makedirs(export_dir, exist_ok=True)

        exported_files = []
        all_docs = [app.documents.item(i) for i in range(app.documents.count)]

        for doc in all_docs:
            doc.activate()
            adsk.doEvents()
            time.sleep(0.3)
            doc_clean = clean_name(doc.name)
            doc_ver = get_version_string(doc)

            # Check if 3D Design
            design = None
            for p in range(doc.products.count):
                design = adsk.fusion.Design.cast(doc.products.item(p))
                if design:
                    break

            if design:
                em = design.exportManager
                rc = design.rootComponent

                # STEP
                try:
                    p_step = os.path.join(export_dir, f"{doc_clean}.step")
                    em.execute(em.createSTEPExportOptions(p_step, rc))
                    if os.path.exists(p_step):
                        exported_files.append((f"{doc_clean}.step", "3D STEP CAD model", doc_ver))
                except Exception:
                    pass

                # STL
                try:
                    p_stl = os.path.join(export_dir, f"{doc_clean}.stl")
                    opts = em.createSTLExportOptions(rc, p_stl)
                    opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
                    em.execute(opts)
                    if os.path.exists(p_stl):
                        exported_files.append((f"{doc_clean}.stl", "3D STL mesh for GitHub preview & 3D printing", doc_ver))
                except Exception:
                    pass

                # 3MF
                try:
                    p_3mf = os.path.join(export_dir, f"{doc_clean}.3mf")
                    opts = em.createC3MFExportOptions(rc, p_3mf)
                    opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
                    em.execute(opts)
                    if os.path.exists(p_3mf):
                        exported_files.append((f"{doc_clean}.3mf", "3D 3MF manufacturing archive", doc_ver))
                except Exception:
                    pass

                # F3D
                try:
                    p_f3d = os.path.join(export_dir, f"{doc_clean}.f3d")
                    em.execute(em.createFusionArchiveExportOptions(p_f3d))
                    if os.path.exists(p_f3d):
                        exported_files.append((f"{doc_clean}.f3d", "Native Fusion 360 3D archive", doc_ver))
                except Exception:
                    pass

            else:
                # 2D PCB or Schematic
                try:
                    if doc.isModified:
                        doc.save("Auto-save before GitHub export")
                        adsk.doEvents()
                        time.sleep(0.5)
                        doc_ver = get_version_string(doc)
                except Exception:
                    pass

                prod_str = " ".join(
                    doc.products.item(p).objectType for p in range(doc.products.count)
                )
                is_board = "Board" in prod_str or "PCB" in prod_str
                ext = ".brd" if is_board else ".sch"
                p_eagle = os.path.join(export_dir, f"{doc_clean}{ext}").replace("\\", "/")

                for cmd in [
                    f'Electron.Command "WRITE \'{p_eagle}\';"',
                    f'Electronics.Command "WRITE \'{p_eagle}\';"',
                ]:
                    if os.path.exists(p_eagle):
                        break
                    try:
                        app.executeTextCommand(cmd)
                        adsk.doEvents()
                        time.sleep(0.3)
                    except Exception:
                        pass

                if os.path.exists(p_eagle):
                    role = "2D PCB layout (Eagle/Fusion)" if is_board else "2D Schematic (Eagle/Fusion)"
                    exported_files.append((f"{doc_clean}{ext}", role, doc_ver))

                # Copy native .fbrd / .fsch from local cache
                native_ext = ".fbrd" if is_board else ".fsch"
                fusion_local = os.path.join(
                    os.environ.get("LOCALAPPDATA", ""), "Autodesk", "Autodesk Fusion 360"
                )
                newest = None
                newest_time = 0
                for root, _, files in os.walk(fusion_local):
                    if "W.login" not in root:
                        continue
                    for f in files:
                        if f.lower().endswith(native_ext):
                            fp = os.path.join(root, f)
                            mt = os.path.getmtime(fp)
                            if mt > newest_time:
                                newest_time = mt
                                newest = fp
                if newest:
                    dst = os.path.join(export_dir, f"{doc_clean}{native_ext}")
                    shutil.copy2(newest, dst)
                    role = "Native Fusion 2D PCB file" if is_board else "Native Fusion 2D Schematic file"
                    exported_files.append((f"{doc_clean}{native_ext}", role, doc_ver))

        # Write VERSION.txt safely after all exports and saves complete
        active_doc.activate()
        main_ver = get_version_string(active_doc)
        lines = [
            f"Main File: {clean_name(active_doc.name)}",
            f"Main Version: {main_ver}",
            f"Full Document Name: {active_doc.name}",
            f"Exported At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=== Exported Files ===",
        ]
        for fname, role, fver in exported_files:
            lines.append(f"- {fname} ({fver}): {role}")

        version_txt_path = os.path.join(export_dir, "VERSION.txt")
        with open(version_txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Open GitHub Desktop
        gh_exe = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "GitHubDesktop", "GitHubDesktop.exe"
        )
        if os.path.exists(gh_exe):
            subprocess.Popen([gh_exe])

    except Exception:
        ui.messageBox(traceback.format_exc(), "Script Error")
