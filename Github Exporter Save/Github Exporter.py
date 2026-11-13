import adsk.core
import adsk.fusion
import traceback
import os
import json
import re
import shutil
import zlib
import struct
from datetime import datetime

ADDIN_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(ADDIN_DIR, "auto_github_export_config.json")

RES_GREEN = os.path.join(ADDIN_DIR, "res_green")
RES_RED = os.path.join(ADDIN_DIR, "res_red")
RES_BLUE = os.path.join(ADDIN_DIR, "res_blue")

TOGGLE_CMD_ID = "AutoGitHubExportToggleBtn_v5"
FOLDER_CMD_ID = "AutoGitHubExportFolderBtn_v5"
NOW_CMD_ID = "AutoGitHubExportNowBtn_v5"

handlers = []
is_exporting = False


def make_solid_png(filepath, r, g, b, size):
    """Generates a valid 32-bit RGBA PNG icon using bytes() so no brackets are needed."""
    filter_none = bytes((0,))
    border_px = bytes((30, 30, 30, 255))
    fill_px = bytes((r, g, b, 255))

    rows = []
    for y in range(size):
        row = bytearray(filter_none)
        for x in range(size):
            if x == 0 or y == 0 or x == size - 1 or y == size - 1:
                row.extend(border_px)
            else:
                row.extend(fill_px)
        rows.append(bytes(row))
    raw_data = b"".join(rows)

    def chunk(tag, data):
        return (
            struct.pack("!I", len(data))
            + tag
            + data
            + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack("!IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw_data))
        + chunk(b"IEND", b"")
    )
    with open(filepath, "wb") as f:
        f.write(png_bytes)


def ensure_icons():
    """Overwrites PNG icons in res_green, res_red, and res_blue."""
    specs = (
        (RES_GREEN, (34, 197, 94)),
        (RES_RED, (239, 68, 68)),
        (RES_BLUE, (59, 130, 246)),
    )
    for folder, rgb in specs:
        os.makedirs(folder, exist_ok=True)
        for sz in (16, 32):
            fpath = os.path.join(folder, f"{sz}x{sz}.png")
            make_solid_png(fpath, *rgb, sz)



def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"enabled": True, "repo_path": ""}


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def clean_name(raw_name):
    no_ver = re.sub(r"\s+v\d+$", "", raw_name.strip())
    cleaned = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in no_ver).strip("_")
    return re.sub(r"_+", "_", cleaned) or "Fusion_Export"


def get_version_string(doc):
    try:
        if doc.dataFile and doc.dataFile.versionNumber:
            return f"v{doc.dataFile.versionNumber}"
    except Exception:
        pass
    m = re.search(r"\b(v\d+)\b", doc.name.strip())
    return m.group(1) if m else "Local Draft"


def detect_electronics_type(doc):
    try:
        if doc.dataFile and doc.dataFile.fileExtension:
            ext = doc.dataFile.fileExtension.lower()
            if "brd" in ext:
                return "board"
            if "sch" in ext:
                return "schematic"
    except Exception:
        pass
    prod_str = " ".join(doc.products.item(p).objectType for p in range(doc.products.count)).lower()
    if "schematic" in prod_str or "sch" in doc.name.lower():
        return "schematic"
    return "board"


def find_cached_file(doc, target_ext):
    fusion_local = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Autodesk", "Autodesk Fusion 360")
    if not os.path.exists(fusion_local):
        return None
    file_id = ""
    try:
        if doc.dataFile and doc.dataFile.id:
            parts = doc.dataFile.id.split(":")
            file_id = parts[-1] if parts else ""
    except Exception:
        pass
    best_match, best_time = None, 0
    for root, _, files in os.walk(fusion_local):
        if "W.login" not in root:
            continue
        for f in files:
            if f.lower().endswith(target_ext):
                fp = os.path.join(root, f)
                if file_id and file_id in f:
                    return fp
                mt = os.path.getmtime(fp)
                if mt > best_time:
                    best_time, best_match = mt, fp
    return best_match


def perform_silent_export(saved_doc, force=False):
    global is_exporting
    if is_exporting:
        return
    cfg = load_config()
    if not force and not cfg.get("enabled", True):
        return
    repo_path = cfg.get("repo_path", "")
    if not repo_path or not os.path.exists(repo_path):
        return

    app = adsk.core.Application.get()
    is_exporting = True
    try:
        active_doc = app.activeDocument or saved_doc
        project_name = clean_name(saved_doc.name)
        export_dir = os.path.join(repo_path, project_name)
        os.makedirs(export_dir, exist_ok=True)
        exported_files = []

        for i in range(app.documents.count):
            doc = app.documents.item(i)
            doc_clean = clean_name(doc.name)
            doc_ver = get_version_string(doc)
            design = None
            for p in range(doc.products.count):
                design = adsk.fusion.Design.cast(doc.products.item(p))
                if design:
                    break

            if design:
                em, rc = design.exportManager, design.rootComponent
                exports_3d = (
                    (".step", lambda p: em.execute(em.createSTEPExportOptions(p, rc)), "3D STEP CAD model"),
                    (".stl", lambda p: em.execute(em.createSTLExportOptions(rc, p)), "3D STL mesh"),
                    (".3mf", lambda p: em.execute(em.createC3MFExportOptions(rc, p)), "3D 3MF archive"),
                    (".f3d", lambda p: em.execute(em.createFusionArchiveExportOptions(p)), "Native Fusion 3D archive"),
                )
                for ext, fn, role in exports_3d:
                    try:
                        out_p = os.path.join(export_dir, doc_clean + ext)
                        fn(out_p)
                        if os.path.exists(out_p):
                            exported_files.append((doc_clean + ext, role, doc_ver))
                    except Exception:
                        pass
            else:
                is_board = detect_electronics_type(doc) == "board"
                if doc == saved_doc:
                    ext = ".brd" if is_board else ".sch"
                    p_eagle = os.path.join(export_dir, doc_clean + ext).replace("\\", "/")
                    cmds = (
                        f'Electron.Command "WRITE \'{p_eagle}\';"',
                        f'Electronics.Command "WRITE \'{p_eagle}\';"',
                    )
                    for cmd in cmds:
                        if os.path.exists(p_eagle):
                            break
                        try:
                            app.executeTextCommand(cmd)
                            adsk.doEvents()
                        except Exception:
                            pass
                    if os.path.exists(p_eagle):
                        exported_files.append((doc_clean + ext, "2D PCB layout" if is_board else "2D Schematic", doc_ver))

                native_ext = ".fbrd" if is_board else ".fsch"
                cached_fp = find_cached_file(doc, native_ext)
                if cached_fp:
                    dst = os.path.join(export_dir, doc_clean + native_ext)
                    shutil.copy2(cached_fp, dst)
                    exported_files.append((doc_clean + native_ext, "Native Fusion 2D PCB" if is_board else "Native Fusion Schematic", doc_ver))

        lines = [
            f"Main File: {project_name}",
            f"Main Version: {get_version_string(saved_doc)}",
            f"Full Name: {saved_doc.name}",
            f"Exported At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=== Exported Files ===",
        ]
        for f_name, f_role, f_ver in exported_files:
            lines.append(f"- {f_name} ({f_ver}): {f_role}")

        with open(os.path.join(export_dir, "VERSION.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        if active_doc:
            active_doc.activate()
    except Exception:
        pass
    finally:
        is_exporting = False


def get_toggle_label(enabled):
    return "GitHub Auto-Export: ON" if enabled else "GitHub Auto-Export: OFF"


class DocumentSavedHandler(adsk.core.DocumentEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        ev = adsk.core.DocumentEventArgs.cast(args)
        if ev and ev.document:
            perform_silent_export(ev.document, force=False)


class ToggleExecHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface
        cfg = load_config()
        new_state = not cfg.get("enabled", True)
        cfg["enabled"] = new_state
        save_config(cfg)

        cmd_def = ui.commandDefinitions.itemById(TOGGLE_CMD_ID)
        if cmd_def:
            cmd_def.name = get_toggle_label(new_state)
            cmd_def.resourceFolder = RES_GREEN if new_state else RES_RED

        ui.messageBox(
            f"GitHub Auto-Export is now {'ON (Green)' if new_state else 'OFF (Red)'}.\n\n"
            f"Target Folder: {cfg.get('repo_path', '')}"
        )


class ToggleCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        on_exec = ToggleExecHandler()
        args.command.execute.add(on_exec)
        handlers.append(on_exec)


class NowExecHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface
        if not app.activeDocument:
            ui.messageBox("No active document open.")
            return
        perform_silent_export(app.activeDocument, force=True)
        ui.messageBox("Export complete!")


class NowCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        on_exec = NowExecHandler()
        args.command.execute.add(on_exec)
        handlers.append(on_exec)


class FolderExecHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface
        cfg = load_config()
        dlg = ui.createFolderDialog()
        dlg.title = "Select Local GitHub Repository Folder"
        if dlg.showDialog() == adsk.core.DialogResults.DialogOK:
            cfg["repo_path"] = dlg.folder
            save_config(cfg)
            ui.messageBox(f"Folder updated:\n{dlg.folder}")


class FolderCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        on_exec = FolderExecHandler()
        args.command.execute.add(on_exec)
        handlers.append(on_exec)


def cleanup_ui(ui):
    qat = ui.toolbars.itemById("QAT")
    if qat:
        for cid in (TOGGLE_CMD_ID, NOW_CMD_ID, FOLDER_CMD_ID):
            c = qat.controls.itemById(cid)
            if c:
                c.deleteMe()

    for pid in ("SolidScriptsAddinsPanel", "PCBScriptsAddinsPanel"):
        panel = ui.allToolbarPanels.itemById(pid)
        if panel:
            for cid in (TOGGLE_CMD_ID, NOW_CMD_ID, FOLDER_CMD_ID):
                c = panel.controls.itemById(cid)
                if c:
                    c.deleteMe()

    for cid in (TOGGLE_CMD_ID, NOW_CMD_ID, FOLDER_CMD_ID):
        d = ui.commandDefinitions.itemById(cid)
        if d:
            d.deleteMe()


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        ensure_icons()
        cleanup_ui(ui)

        cfg = load_config()
        if not cfg.get("repo_path") or not os.path.exists(cfg["repo_path"]):
            dlg = ui.createFolderDialog()
            dlg.title = "Select Your Local GitHub Repository Folder"
            if dlg.showDialog() != adsk.core.DialogResults.DialogOK:
                return
            cfg["repo_path"] = dlg.folder
            cfg.setdefault("enabled", True)
            save_config(cfg)

        is_on = cfg.get("enabled", True)
        toggle_icon_dir = RES_GREEN if is_on else RES_RED

        buttons = (
            (TOGGLE_CMD_ID, get_toggle_label(is_on), "Toggle auto-export on save", ToggleCreatedHandler(), toggle_icon_dir, True),
            (NOW_CMD_ID, "GitHub Export Now", "Export open files immediately", NowCreatedHandler(), RES_BLUE, True),
            (FOLDER_CMD_ID, "GitHub Export Folder...", "Change target GitHub repository folder", FolderCreatedHandler(), RES_BLUE, False),
        )

        qat = ui.toolbars.itemById("QAT")

        for cid, label, tip, created_handler, icon_dir, put_in_top_bar in buttons:
            cdef = ui.commandDefinitions.addButtonDefinition(cid, label, tip, icon_dir)
            cdef.commandCreated.add(created_handler)
            handlers.append(created_handler)

            if put_in_top_bar and qat:
                if qat.controls.itemById("SaveCommand"):
                    qat.controls.addCommand(cdef, "SaveCommand", False)
                else:
                    qat.controls.addCommand(cdef)

            for pid in ("SolidScriptsAddinsPanel", "PCBScriptsAddinsPanel"):
                panel = ui.allToolbarPanels.itemById(pid)
                if panel:
                    ctrl = panel.controls.addCommand(cdef)
                    ctrl.isPromoted = put_in_top_bar
                    ctrl.isPromotedByDefault = put_in_top_bar

        on_saved = DocumentSavedHandler()
        app.documentSaved.add(on_saved)
        handlers.append(on_saved)

        if not context.get("IsApplicationStartup", False):
            ui.messageBox(
                "GitHub Auto-Export Add-In is active!\n\n"
                "Look next to Save in the top bar:\n"
                "• Green / Red square = Toggle Auto-Export ON / OFF\n"
                "• Blue square = Export Now"
            )

    except Exception:
        if ui:
            ui.messageBox(traceback.format_exc(), "Add-In Error")


def stop(context):
    app = adsk.core.Application.get()
    cleanup_ui(app.userInterface)
    for h in handlers:
        try:
            app.documentSaved.remove(h)
        except Exception:
            pass
    handlers.clear()
