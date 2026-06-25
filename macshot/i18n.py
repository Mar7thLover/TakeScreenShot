"""Small runtime translation helpers for the desktop UI."""

from __future__ import annotations

import locale

LANG_AUTO = "auto"
LANG_EN = "en"
LANG_ZH = "zh"
SUPPORTED_LANGUAGES = (LANG_AUTO, LANG_EN, LANG_ZH)

LANGUAGE_NAMES = {
    LANG_AUTO: "Auto / 自动",
    LANG_EN: "English",
    LANG_ZH: "简体中文",
}

_STRINGS = {
    LANG_EN: {
        "app.running": "Macshot is running.",
        "app.already_running": "Macshot is already running. Use the existing tray icon.",
        "app.capture_failed": "Macshot capture failed",
        "app.hotkey_unavailable": "Macshot hotkey unavailable",
        "app.hotkey_register_error": "Could not register hotkey: {hotkey}\n\n{error}",
        "app.hotkey_registered_elsewhere": "The hotkey is already registered by another app.",
        "app.hotkey_windows_error": "Windows error {code}.",
        "app.hotkey_tray_fallback": "Macshot will keep running. Use the tray menu to capture windows.",
        "app.tray_required": "The 'pystray' package is required for the Macshot tray app.",
        "app.tray_title": "Macshot - {hotkey} to capture",
        "notify.running_title": "Macshot is running",
        "notify.running": "Press {hotkey} to capture a window.",
        "notify.running_no_hotkey": "Use the tray menu to capture windows.",
        "notify.saved": "Saved to {path}",
        "notify.saved_click": "Saved to {path}\nClick to open the output folder.",
        "notify.open_folder": "Open folder",
        "tray.home": "Home",
        "tray.capture_window": "Capture Window",
        "tray.capture_full": "Capture Full Screen",
        "tray.capture_region": "Capture Region",
        "tray.capture_circle": "Capture Circle",
        "tray.capture_freeform": "Free-form Screenshot",
        "tray.settings": "Settings",
        "tray.open_folder": "Open Output Folder",
        "tray.exit": "Exit",
        "home.subtitle": "macOS-style screenshots for Windows",
        "home.capture_section": "CAPTURE",
        "home.hotkey": "Hotkey: {hotkey}",
        "home.output": "Output: {path}",
        "home.last_saved": "Last saved: {path}",
        "home.last_saved_none": "Last saved: none this session",
        "home.capture_window": "Capture Window",
        "home.capture_full": "Capture Full Screen",
        "home.capture_region": "Capture Region",
        "home.capture_circle": "Capture Circle",
        "home.capture_freeform": "Free-form Screenshot",
        "home.settings": "Settings",
        "home.open_folder": "Open Output Folder",
        "home.close": "Close",
        "settings.title": "Settings",
        "settings.window_title": "Macshot Settings",
        "settings.section_general": "GENERAL",
        "settings.section_style": "STYLE",
        "settings.output_folder": "Output folder",
        "settings.hotkey": "Hotkey",
        "settings.language": "Language",
        "settings.settle_seconds": "Settle seconds",
        "settings.corner_radius": "Corner radius",
        "settings.padding": "Padding",
        "settings.shadow_opacity": "Shadow opacity",
        "settings.shadow_blur": "Shadow blur",
        "settings.shadow_offset": "Shadow offset",
        "settings.open_after": "Open folder after capture",
        "settings.copy_clipboard": "Copy result to clipboard",
        "settings.raise_window": "Bring window to front before capture",
        "settings.enable_shadow": "Enable shadow",
        "settings.browse": "Browse",
        "settings.save": "Save",
        "settings.cancel": "Cancel",
        "error.must_int": "{name} must be an integer.",
        "error.must_number": "{name} must be a number.",
        "error.non_negative": "{name} must be zero or greater.",
        "picker.window_hint": "Click a window to capture    ·    Esc / right-click to cancel",
        "picker.region_hint": "Drag a rectangular region    ·    Esc / right-click to cancel",
        "picker.circle_hint": "Drag a circle region    ·    Esc / right-click to cancel",
        "picker.freeform_hint": "Draw a free-form shape    ·    Release to capture    ·    Esc / right-click to cancel",
    },
    LANG_ZH: {
        "app.running": "Macshot 正在运行。",
        "app.already_running": "Macshot 已在运行，请使用现有的托盘图标。",
        "app.capture_failed": "Macshot 截图失败",
        "app.hotkey_unavailable": "Macshot 快捷键不可用",
        "app.hotkey_register_error": "无法注册快捷键：{hotkey}\n\n{error}",
        "app.hotkey_registered_elsewhere": "该快捷键已被其他应用占用。",
        "app.hotkey_windows_error": "Windows 错误 {code}。",
        "app.hotkey_tray_fallback": "Macshot 会继续运行。请使用托盘菜单进行截图。",
        "app.tray_required": "Macshot 托盘应用需要安装 'pystray' 套件。",
        "app.tray_title": "Macshot - {hotkey} 截图",
        "notify.running_title": "Macshot 正在运行",
        "notify.running": "按 {hotkey} 截取窗口。",
        "notify.running_no_hotkey": "请使用托盘菜单进行截图。",
        "notify.saved": "已保存到 {path}",
        "notify.saved_click": "已保存到 {path}\n点击打开输出文件夹。",
        "notify.open_folder": "打开文件夹",
        "tray.home": "主页",
        "tray.capture_window": "截取窗口",
        "tray.capture_full": "截取全屏",
        "tray.capture_region": "截取部分画面",
        "tray.capture_circle": "圆形截图",
        "tray.capture_freeform": "自由形状截图",
        "tray.settings": "设置",
        "tray.open_folder": "打开输出文件夹",
        "tray.exit": "退出",
        "home.subtitle": "适用于 Windows 的 macOS 风格截图工具",
        "home.capture_section": "截图",
        "home.hotkey": "快捷键：{hotkey}",
        "home.output": "输出位置：{path}",
        "home.last_saved": "上次保存：{path}",
        "home.last_saved_none": "本次运行尚未截图",
        "home.capture_window": "截取窗口",
        "home.capture_full": "截取全屏",
        "home.capture_region": "截取部分画面",
        "home.capture_circle": "圆形截图",
        "home.capture_freeform": "自由形状截图",
        "home.settings": "设置",
        "home.open_folder": "打开输出文件夹",
        "home.close": "关闭",
        "settings.title": "设置",
        "settings.window_title": "Macshot 设置",
        "settings.section_general": "常规",
        "settings.section_style": "样式",
        "settings.output_folder": "输出文件夹",
        "settings.hotkey": "快捷键",
        "settings.language": "语言",
        "settings.settle_seconds": "等待秒数",
        "settings.corner_radius": "圆角半径",
        "settings.padding": "边距",
        "settings.shadow_opacity": "阴影透明度",
        "settings.shadow_blur": "阴影模糊",
        "settings.shadow_offset": "阴影偏移",
        "settings.open_after": "截图后打开文件夹",
        "settings.copy_clipboard": "复制截图到剪贴板",
        "settings.raise_window": "截图前置顶目标窗口",
        "settings.enable_shadow": "启用阴影",
        "settings.browse": "浏览",
        "settings.save": "保存",
        "settings.cancel": "取消",
        "error.must_int": "{name} 必须是整数。",
        "error.must_number": "{name} 必须是数字。",
        "error.non_negative": "{name} 必须大于或等于零。",
        "picker.window_hint": "点击要截取的窗口    ·    Esc / 右键取消",
        "picker.region_hint": "拖拽选择矩形区域    ·    Esc / 右键取消",
        "picker.circle_hint": "拖拽选择圆形区域    ·    Esc / 右键取消",
        "picker.freeform_hint": "按住左键绘制自由形状    ·    松开完成截图    ·    Esc / 右键取消",
    },
}


def resolve_language(language: str | None) -> str:
    """Resolve persisted language settings to a concrete language code."""
    if language in {LANG_EN, LANG_ZH}:
        return language
    try:
        system_language = (locale.getlocale()[0] or "").lower()
    except Exception:
        system_language = ""
    return LANG_ZH if system_language.startswith("zh") else LANG_EN


def language_label(language: str) -> str:
    return LANGUAGE_NAMES.get(language, language)


def translate(key: str, language: str | None = LANG_AUTO, **values) -> str:
    lang = resolve_language(language)
    template = _STRINGS.get(lang, _STRINGS[LANG_EN]).get(key)
    if template is None:
        template = _STRINGS[LANG_EN].get(key, key)
    return template.format(**values) if values else template
