from __future__ import annotations

from ui.widgets.ansi import (
    AnsiStyle,
    iter_styled_chars,
    parse_ansi,
    strip_ansi,
    style_key,
)


class TestParseAnsi:
    def test_plain_text_returns_single_segment(self):
        segs = parse_ansi("hello world")
        assert len(segs) == 1
        assert segs[0].text == "hello world"
        assert segs[0].style.fg is None

    def test_empty_string(self):
        assert parse_ansi("") == []

    def test_no_ansi_keeps_style_empty(self):
        segs = parse_ansi("abc")
        s = segs[0].style
        assert not any([s.fg, s.bg, s.bold, s.dim, s.italic, s.underline, s.inverse])

    def test_basic_red(self):
        segs = parse_ansi("\x1b[31mRED\x1b[0m")
        assert len(segs) == 1
        assert segs[0].text == "RED"
        assert segs[0].style.fg == "#ff5f57"

    def test_basic_red_with_followup_text(self):
        segs = parse_ansi("\x1b[31mRED\x1b[0m END")
        assert len(segs) == 2
        assert segs[0].text == "RED"
        assert segs[0].style.fg == "#ff5f57"
        assert segs[1].text == " END"
        assert segs[1].style.fg is None

    def test_multiple_attrs_in_one_sequence(self):
        segs = parse_ansi("\x1b[1;31;42mBOLD-RED-ON-GREEN\x1b[0m")
        s = segs[0].style
        assert s.bold is True
        assert s.fg == "#ff5f57"
        assert s.bg == "#28c840"

    def test_256_color(self):
        segs = parse_ansi("\x1b[38;5;208mORANGE\x1b[0mEND")
        s = segs[0].style
        # 208 lands in the 6x6x6 cube: idx - 16 = 192 → r=192//36=5,
        # g=(192//6)%6=2, b=192%6=0 → levels[5]=255, levels[2]=135, levels[0]=0
        assert s.fg == "#ff8700"
        assert segs[1].text == "END"
        assert segs[1].style.fg is None

    def test_truecolor(self):
        segs = parse_ansi("\x1b[38;2;255;100;50mSALMON\x1b[0m")
        assert segs[0].style.fg == "#ff6432"

    def test_underline_and_bold(self):
        segs = parse_ansi("\x1b[4mUNDER\x1b[0m \x1b[1mBOLD\x1b[0mPLAIN")
        assert segs[0].style.underline is True
        assert segs[0].text == "UNDER"
        assert segs[1].text == " "
        assert segs[2].style.bold is True
        assert segs[2].text == "BOLD"
        assert segs[3].text == "PLAIN"
        assert segs[3].style.bold is False

    def test_strip_removes_all_sequences(self):
        text = "\x1b[31m\x1b[1mHELLO\x1b[0m \x1b[38;5;200mWORLD\x1b[0m"
        assert strip_ansi(text) == "HELLO WORLD"

    def test_cursor_movement_is_dropped(self):
        text = "AAA\x1b[2K\x1b[1GZZZ"
        # \x1b[2K = erase line, \x1b[1G = move to col 1 — both stripped
        assert strip_ansi(text) == "AAAZZZ"

    def test_style_key_stable(self):
        s1 = AnsiStyle(fg="#ff0000", bold=True)
        s2 = AnsiStyle(bold=True, fg="#ff0000")
        assert style_key(s1) == style_key(s2)

    def test_iter_styled_chars_per_char(self):
        text = "\x1b[31mAB\x1b[0mC"
        chars = list(iter_styled_chars(text))
        assert len(chars) == 3
        assert chars[0] == (AnsiStyle(fg="#ff5f57"), "A")
        assert chars[1] == (AnsiStyle(fg="#ff5f57"), "B")
        assert chars[2][0].fg is None
        assert chars[2][1] == "C"

    def test_reset_clears_all(self):
        segs = parse_ansi("\x1b[1;31;4mX\x1b[0mY")
        after = segs[1].style  # Y comes after reset (0m)
        assert after.bold is False
        assert after.fg is None
        assert after.underline is False

    def test_subsequent_segments_carry_state(self):
        segs = parse_ansi("\x1b[31mRED \x1b[1mBOLD\x1b[0m END")
        # After "RED ", still red. Then \x1b[1m adds bold. Then text. Then
        # \x1b[0m resets. Then " END" should be default.
        red_seg = segs[0]
        bold_seg = segs[1]
        end_seg = segs[2]
        assert red_seg.style.fg == "#ff5f57"
        assert bold_seg.style.fg == "#ff5f57"
        assert bold_seg.style.bold is True
        assert end_seg.style.fg is None
        assert end_seg.text == " END"

    def test_empty_param_is_reset(self):
        segs = parse_ansi("\x1b[1mBOLD\x1b[mPLAIN")
        # Bare \x1b[m = reset
        after = segs[1].style
        assert after.bold is False
        assert after.fg is None

    def test_default_color_unset_via_39_49(self):
        segs = parse_ansi("\x1b[31mRED\x1b[39mPLAIN")
        assert segs[0].style.fg == "#ff5f57"
        assert segs[1].style.fg is None

    def test_xterm256_grayscale_range(self):
        # 232..255: grayscale ramp
        for idx in (232, 240, 255):
            segs = parse_ansi(f"\x1b[38;5;{idx}mGRAY\x1b[0mEND")
            fg = segs[0].style.fg
            assert fg is not None
            assert fg.startswith("#")
            hex_ = fg.lstrip("#")
            assert hex_[0:2] == hex_[2:4] == hex_[4:6]
            assert segs[1].style.fg is None
