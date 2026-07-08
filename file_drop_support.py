# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # pragma: no cover - optional dependency.
    DND_FILES = None
    TkinterDnD = None


def create_tk_root() -> tk.Tk:
    if TkinterDnD is not None:
        return TkinterDnD.Tk()
    return tk.Tk()


def enable_file_drop(root: tk.Tk, targets: list[tk.Widget], callback, log=None) -> bool:
    manager = FileDropManager(root, callback, log=log)
    enabled = manager.enable(targets)
    if enabled:
        managers = getattr(root, "_file_drop_managers", [])
        managers.append(manager)
        setattr(root, "_file_drop_managers", managers)
    return enabled


class FileDropManager:
    def __init__(self, root: tk.Tk, callback, log=None):
        self.root = root
        self.callback = callback
        self.log = log
        self._drop_targets: dict[int, object] = {}
        self._ole32 = None
        self._shell32 = None

    def enable(self, targets: list[tk.Widget]) -> bool:
        widgets = self._unique_widgets(targets)
        if DND_FILES is not None and self._enable_tkinterdnd(widgets):
            return True
        if os.name == "nt":
            return self._enable_windows_drop(widgets)
        return False

    def _enable_tkinterdnd(self, widgets: list[tk.Widget]) -> bool:
        enabled = False
        for widget in widgets:
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._handle_tkinterdnd_drop)
                enabled = True
            except (AttributeError, tk.TclError):
                continue
        return enabled

    def _handle_tkinterdnd_drop(self, event):
        paths = [Path(item) for item in self.root.tk.splitlist(event.data)]
        self.callback(paths)
        return "break"

    def _enable_windows_drop(self, widgets: list[tk.Widget]) -> bool:
        try:
            import ctypes
            from ctypes import wintypes
        except Exception as exc:  # pragma: no cover - Windows only.
            self._log(f"启用文件拖拽失败：{exc}")
            return False

        ole32 = ctypes.OleDLL("ole32")
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        self._ole32 = ole32
        self._shell32 = shell32

        ole32.OleInitialize.argtypes = [ctypes.c_void_p]
        ole32.OleInitialize.restype = ctypes.HRESULT
        ole32.RegisterDragDrop.argtypes = [wintypes.HWND, ctypes.c_void_p]
        ole32.RegisterDragDrop.restype = ctypes.HRESULT
        ole32.RevokeDragDrop.argtypes = [wintypes.HWND]
        ole32.RevokeDragDrop.restype = ctypes.HRESULT
        ole32.ReleaseStgMedium.argtypes = [ctypes.c_void_p]
        ole32.ReleaseStgMedium.restype = None

        initialized = ole32.OleInitialize(None)
        if initialized not in (0, 1):
            self._log(f"启用文件拖拽失败，OLE 初始化错误码：{initialized}")
            return False

        enabled = False
        for widget in widgets:
            try:
                widget.update_idletasks()
                hwnd = wintypes.HWND(int(widget.winfo_id()))
            except (tk.TclError, ValueError):
                continue

            hwnd_value = int(hwnd.value)
            if hwnd_value in self._drop_targets:
                continue

            drop_target = _WindowsDropTarget(self)
            result = ole32.RegisterDragDrop(hwnd, drop_target.pointer)
            if result != 0:
                # 0x80040101 means the widget already has a drop target. Treat it
                # as unavailable and keep the normal file picker path intact.
                if result != -2147221247:
                    self._log(f"启用文件拖拽失败，错误码：{result}")
                continue

            self._drop_targets[hwnd_value] = drop_target
            widget.bind(
                "<Destroy>",
                lambda _event, registered_hwnd=hwnd_value: self._revoke_windows_drop(
                    registered_hwnd
                ),
                add="+",
            )
            enabled = True

        return enabled

    def _revoke_windows_drop(self, hwnd_value: int) -> None:
        drop_target = self._drop_targets.pop(hwnd_value, None)
        if drop_target is None or self._ole32 is None:
            return
        try:
            self._ole32.RevokeDragDrop(hwnd_value)
        except Exception:
            pass

    def _query_windows_data_object_files(self, data_object) -> list[Path]:
        import ctypes
        from ctypes import wintypes

        ole32 = self._ole32
        shell32 = self._shell32
        if ole32 is None or shell32 is None:
            return []

        class FORMATETC(ctypes.Structure):
            _fields_ = [
                ("cfFormat", wintypes.WORD),
                ("ptd", ctypes.c_void_p),
                ("dwAspect", wintypes.DWORD),
                ("lindex", wintypes.LONG),
                ("tymed", wintypes.DWORD),
            ]

        class STGMEDIUM_UNION(ctypes.Union):
            _fields_ = [
                ("hGlobal", wintypes.HGLOBAL),
                ("pstm", ctypes.c_void_p),
                ("pstg", ctypes.c_void_p),
            ]

        class STGMEDIUM(ctypes.Structure):
            _fields_ = [
                ("tymed", wintypes.DWORD),
                ("u", STGMEDIUM_UNION),
                ("pUnkForRelease", ctypes.c_void_p),
            ]

        get_data_type = ctypes.WINFUNCTYPE(
            ctypes.HRESULT,
            ctypes.c_void_p,
            ctypes.POINTER(FORMATETC),
            ctypes.POINTER(STGMEDIUM),
        )
        data_object_vtable = ctypes.cast(
            data_object,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)),
        ).contents
        get_data = get_data_type(data_object_vtable[3])

        formatetc = FORMATETC(15, None, 1, -1, 1)
        medium = STGMEDIUM()
        result = get_data(data_object, ctypes.byref(formatetc), ctypes.byref(medium))
        if result != 0:
            return []

        shell32.DragQueryFileW.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
            wintypes.LPWSTR,
            wintypes.UINT,
        ]
        shell32.DragQueryFileW.restype = wintypes.UINT

        try:
            count = shell32.DragQueryFileW(medium.u.hGlobal, 0xFFFFFFFF, None, 0)
            paths: list[Path] = []
            for index in range(count):
                length = shell32.DragQueryFileW(medium.u.hGlobal, index, None, 0)
                buffer = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(medium.u.hGlobal, index, buffer, length + 1)
                if buffer.value:
                    paths.append(Path(buffer.value))
            return paths
        finally:
            ole32.ReleaseStgMedium(ctypes.byref(medium))

    def _unique_widgets(self, widgets: list[tk.Widget]) -> list[tk.Widget]:
        unique: list[tk.Widget] = []
        seen: set[str] = set()
        for widget in widgets:
            key = str(widget)
            if key in seen:
                continue
            seen.add(key)
            unique.append(widget)
        return unique

    def _log(self, message: str) -> None:
        if self.log:
            self.log(message)


class _WindowsDropTarget:
    def __init__(self, manager: FileDropManager):
        import ctypes
        from ctypes import wintypes

        self.manager = manager
        self._ref_count = 1
        self._iid_iunknown = bytes.fromhex("0000000000000000c000000000000046")
        self._iid_idroptarget = bytes.fromhex("2201000000000000c000000000000046")

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        class POINTL(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class COMObject(ctypes.Structure):
            _fields_ = [("lpVtbl", ctypes.POINTER(ctypes.c_void_p))]

        query_interface_type = ctypes.WINFUNCTYPE(
            ctypes.HRESULT,
            ctypes.c_void_p,
            ctypes.POINTER(GUID),
            ctypes.POINTER(ctypes.c_void_p),
        )
        add_ref_type = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
        release_type = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
        drag_enter_type = ctypes.WINFUNCTYPE(
            ctypes.HRESULT,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            POINTL,
            ctypes.POINTER(wintypes.DWORD),
        )
        drag_over_type = ctypes.WINFUNCTYPE(
            ctypes.HRESULT,
            ctypes.c_void_p,
            wintypes.DWORD,
            POINTL,
            ctypes.POINTER(wintypes.DWORD),
        )
        drag_leave_type = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p)
        drop_type = ctypes.WINFUNCTYPE(
            ctypes.HRESULT,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            POINTL,
            ctypes.POINTER(wintypes.DWORD),
        )

        self._callbacks = [
            query_interface_type(self._query_interface),
            add_ref_type(self._add_ref),
            release_type(self._release),
            drag_enter_type(self._drag_enter),
            drag_over_type(self._drag_over),
            drag_leave_type(self._drag_leave),
            drop_type(self._drop),
        ]
        self._vtable = (ctypes.c_void_p * len(self._callbacks))(
            *[ctypes.cast(callback, ctypes.c_void_p).value for callback in self._callbacks]
        )
        self._object = COMObject()
        self._object.lpVtbl = ctypes.cast(self._vtable, ctypes.POINTER(ctypes.c_void_p))
        self.pointer = ctypes.cast(ctypes.pointer(self._object), ctypes.c_void_p)

    def _query_interface(self, _this, riid, ppv):
        import ctypes

        if not ppv:
            return -2147467262  # E_NOINTERFACE

        iid = ctypes.string_at(ctypes.addressof(riid.contents), 16)
        if iid in {self._iid_iunknown, self._iid_idroptarget}:
            ppv[0] = self.pointer.value
            self._add_ref(_this)
            return 0

        ppv[0] = 0
        return -2147467262  # E_NOINTERFACE

    def _add_ref(self, _this):
        self._ref_count += 1
        return self._ref_count

    def _release(self, _this):
        self._ref_count = max(1, self._ref_count - 1)
        return self._ref_count

    def _drag_enter(self, _this, _data_object, _key_state, _point, effect):
        self._set_copy_effect(effect)
        return 0

    def _drag_over(self, _this, _key_state, _point, effect):
        self._set_copy_effect(effect)
        return 0

    def _drag_leave(self, _this):
        return 0

    def _drop(self, _this, data_object, _key_state, _point, effect):
        try:
            paths = self.manager._query_windows_data_object_files(data_object)
            if paths:
                self.manager.root.after(
                    0,
                    lambda dropped_paths=paths: self.manager.callback(dropped_paths),
                )
            self._set_copy_effect(effect)
            return 0
        except Exception as exc:
            self.manager._log(f"读取拖入文件失败：{exc}")
            return 0

    def _set_copy_effect(self, effect) -> None:
        if effect:
            effect[0] = 1
