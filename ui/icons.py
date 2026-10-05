"""Line icons rendered with CSS masks (24x24, colour = currentColor). No downloads, no external requests.

Paths follow the Lucide icon set (https://lucide.dev, ISC licence).
"""

from __future__ import annotations

_PATHS: dict[str, str] = {
    "sparkles": (
        '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 '
        '9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 '
        '.964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>'
        '<path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>'
    ),
    "graduation": (
        '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 '
        '1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>'
    ),
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "handshake": (
        '<path d="m11 17 2 2a1 1 0 1 0 3-3"/>'
        '<path d="m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 '
        '5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4"/><path d="m21 3 1 11h-2"/>'
        '<path d="M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3"/><path d="M3 4h8"/>'
    ),
    "compass": (
        '<circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804'
        '-5.411a2 2 0 0 1 1.265-1.265z"/>'
    ),
    "message": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "inbox": (
        '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 '
        '0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
    ),
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "mail": (
        '<rect width="20" height="16" x="2" y="4" rx="2"/>'
        '<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
}


def _svg(name: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</svg>'
    )


def icon_css() -> str:
    """CSS defining each icon as a mask. st.html strips <svg> tags, so icons live in the stylesheet."""
    from urllib.parse import quote

    base = (
        ".fx-ico{display:inline-block;flex:0 0 auto;vertical-align:-0.2em;background-color:currentColor;"
        "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;-webkit-mask-position:center;mask-position:center;"
        "-webkit-mask-size:contain;mask-size:contain}"
    )
    rules = [base]
    for name in _PATHS:
        url = "data:image/svg+xml," + quote(_svg(name), safe="")
        rules.append(f'.fx-ico-{name}{{-webkit-mask-image:url("{url}");mask-image:url("{url}")}}')
    return "".join(rules)


def icon_svg(name: str, size: int = 20) -> str:
    """Return an icon element (a styled span) for a known icon name, or an empty string."""
    if name not in _PATHS:
        return ""
    px = int(size)
    return f'<span class="fx-ico fx-ico-{name}" style="width:{px}px;height:{px}px" aria-hidden="true"></span>'
