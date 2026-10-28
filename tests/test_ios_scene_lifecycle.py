"""iOS 27 stops an app at launch unless it adopts the scene lifecycle.

TestFlight build 587 crashed ~160 ms after opening on every iOS 27 iPhone
(UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption). Both plists
must name the scene delegate and the Main storyboard, and the delegate must
be compiled into the App target.
"""
import plistlib
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "ui" / "ios" / "App"


@pytest.mark.parametrize("name", ["Info.plist", "Info-Debug.plist"])
def test_plist_declares_the_scene(name):
    plist = plistlib.loads((APP / "App" / name).read_bytes())
    assert "UIMainStoryboardFile" not in plist
    manifest = plist["UIApplicationSceneManifest"]
    assert manifest["UIApplicationSupportsMultipleScenes"] is False
    (config,) = manifest["UISceneConfigurations"]["UIWindowSceneSessionRoleApplication"]
    assert config["UISceneDelegateClassName"] == "$(PRODUCT_MODULE_NAME).SceneDelegate"
    assert config["UISceneStoryboardFile"] == "Main"


def test_scene_delegate_is_built_into_the_app():
    assert (APP / "App" / "SceneDelegate.swift").is_file()
    project = (APP / "App.xcodeproj" / "project.pbxproj").read_text()
    assert "SceneDelegate.swift in Sources */," in project
