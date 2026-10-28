"""Home-screen widget layouts must only use views a RemoteViews can inflate.

A widget is drawn by the launcher, not the app, and the launcher inflates
the layout through a filter that accepts only classes marked @RemoteView.
Plain <View> and <Space> are not among them: a layout holding one compiles,
passes aapt and draws fine inside the app, then shows "Couldn't add widget"
in the picker and "Can't load widget" on the home screen. That is how the
Calendar, Today's Subhashita and the large Your day widget broke in build
#230 (Hawk, 2026-10-23): each had a <View> spacer or rule. Use an empty
<FrameLayout> instead.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

LAYOUTS = (
    Path(__file__).resolve().parent.parent
    / "ui" / "android" / "app" / "src" / "main" / "res" / "layout"
)

# Views RemoteViews accepts on every Android the app supports (minSdk 24).
REMOTE_VIEWS = {
    "FrameLayout", "LinearLayout", "RelativeLayout", "GridLayout",
    "AnalogClock", "Button", "Chronometer", "ImageButton", "ImageView",
    "ProgressBar", "TextView", "TextClock", "ViewFlipper", "ListView",
    "GridView", "StackView", "AdapterViewFlipper",
}


def test_widget_layouts_use_only_remote_views():
    layouts = sorted(LAYOUTS.glob("widget_*.xml"))
    assert layouts, "no widget layouts found"
    bad = []
    for path in layouts:
        for element in ET.parse(path).iter():
            if element.tag not in REMOTE_VIEWS:
                bad.append(f"{path.name}: <{element.tag}>")
    assert not bad, "not allowed in a widget (use FrameLayout): " + ", ".join(bad)


# Rows added into a widget at draw time, and the picker's static previews.
NOT_A_WIDGET = {"widget_calendar_event.xml", "widget_calendar_week_day.xml"}


def test_every_widget_card_can_fade():
    """The reader's opacity setting fades the ImageView widget_bg behind each
    widget (Widgets.applyOpacity). A layout without one ignores the setting."""
    missing = [
        path.name
        for path in sorted(LAYOUTS.glob("widget_*.xml"))
        if path.name not in NOT_A_WIDGET
        and not path.name.endswith("_preview.xml")
        and "@+id/widget_bg" not in path.read_text()
    ]
    assert not missing, "no widget_bg card: " + ", ".join(missing)
