"""Trang KOC: sửa an toàn, chặn tuổi < 22, Lớp B/negative/lock, từ cấm, mạo danh, ready khi chưa có ảnh."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from agnet.koc import master_prompt as mp  # noqa: E402
from agnet.ui import page_koc as K  # noqa: E402

CID = "KOC-01-MAI"


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def env(tmp_path):
    d = tmp_path / "characters"
    shutil.copytree(mp.CHAR_DIR, d)
    y = tmp_path / "characters.yaml"
    shutil.copy(mp.ROOT / "config" / "characters.yaml", y)
    return d, y, tmp_path / "refs_root"


def load(d):
    return json.loads((d / "koc-01-mai.json").read_text(encoding="utf-8"))


def test_safe_edit_saved(env):
    d, y, r = env
    K.save_character(d, y, CID, {"meta.voice": "Bắc, chậm", "age": 23}, refs_root=r)
    c = load(d)
    assert c["meta"]["voice"] == "Bắc, chậm" and "23 years old" in c["identity"]["demographics"]
    assert not list(d.glob("*.tmp"))


def test_age_21_rejected_and_nothing_written(env):
    d, y, r = env
    before = (d / "koc-01-mai.json").read_text(encoding="utf-8")
    with pytest.raises(K.KocError, match="22"):
        K.save_character(d, y, CID, {"age": 21, "meta.voice": "x"}, refs_root=r)
    assert (d / "koc-01-mai.json").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("path", ["realism_engine", "negative", "consistency_lock", "negative.0",
                                  "identity.face_structure", "realism_engine.skin"])
def test_locked_paths_rejected(env, path):
    d, y, r = env
    with pytest.raises(K.KocLocked):
        K.save_character(d, y, CID, {path: "hack"}, refs_root=r)


@pytest.mark.parametrize("bad", ["sexy outfit", "perfect skin", "90-60-90", "Tôi là bác sĩ chuyên khoa",
                                 "I am a lawyer"])
def test_banned_text_rejected(env, bad):
    d, y, r = env
    with pytest.raises(K.KocError):
        K.save_character(d, y, CID, {"identity.persona": bad}, refs_root=r)


def test_negated_doctor_allowed(env):
    d, y, r = env
    K.save_character(d, y, CID, {"identity.persona": "friendly; không phải bác sĩ, chỉ chia sẻ kinh nghiệm"}, refs_root=r)


def test_ready_blocked_without_reference_images(env):
    d, y, r = env
    with pytest.raises(K.KocError, match="ảnh gốc"):
        K.save_character(d, y, CID, {}, status="ready", refs_root=r)
    assert "KOC-01-MAI,  file: koc-01-mai.json,  status: draft" in y.read_text(encoding="utf-8")


def test_ready_allowed_when_images_exist(env):
    d, y, r = env
    for ref in load(d)["identity"]["reference_images"]:
        (r / ref).parent.mkdir(parents=True, exist_ok=True)
        (r / ref).write_bytes(b"x")
    K.save_character(d, y, CID, {}, status="ready", refs_root=r)
    assert K.list_characters(d, y)[0]["status"] == "ready"
    assert y.read_text(encoding="utf-8").count("status: ready") == 1


def test_preview_prompt_readonly_and_untouched(env):
    d, y, r = env
    c = load(d)
    p = K.preview_prompt(c)
    mp.assert_untouched(p)
    assert load(d) == c


def test_page_save_and_block(qapp, env):
    d, y, r = env
    pg = K.KocPage(d, y, r)
    assert pg.list.count() == 5 and "ai_disclosure" in pg.disclosure.text()
    pg.list.setCurrentRow(0)
    pg.age.setValue(21)
    pg.save()
    assert "Chưa lưu" in pg.msg.text()
    pg.age.setValue(23)
    pg.edits["meta.voice"].setText("giọng mới")
    pg.save()
    assert pg.msg.text() == "Đã lưu." and load(d)["meta"]["voice"] == "giọng mới"
    pg.status.setCurrentText("ready")
    pg.save()
    assert "ảnh gốc" in pg.msg.text()
    pg.show_prompt()
    assert '"consistency_lock"' in pg.prompt_view.toPlainText()
    assert pg.locked.isReadOnly()
