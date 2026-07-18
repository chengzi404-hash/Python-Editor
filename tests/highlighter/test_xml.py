import pytest

from core.language.highlighter import HighlightBlock
from core.language.highlighter.xml_expert import XmlHighlighterExpert


class TestXmlHighlighterExpert:
    def test_init(self):
        expert = XmlHighlighterExpert()
        assert expert is not None

    def test_get_language_exts(self):
        expert = XmlHighlighterExpert()
        exts = expert.get_languange_exts()
        assert "xml" in exts
        assert "html" in exts
        assert "xhtml" in exts
        assert "svg" in exts

    def test_highlight_empty_string(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="")
        result = expert.highlight(block)
        assert result.code == ""
        assert result.tokens == []

    def test_highlight_comment(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="<!-- comment -->")
        result = expert.highlight(block)
        assert result.code == "<!-- comment -->"
        assert result.tokens is not None
        comment_tokens = [t for t in result.tokens if t.type == "comment"]
        assert len(comment_tokens) == 1

    def test_highlight_tag(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="<tag>")
        result = expert.highlight(block)
        assert result.code == "<tag>"
        assert result.tokens is not None
        tag_tokens = [t for t in result.tokens if t.type == "tag"]
        assert len(tag_tokens) == 1

    def test_highlight_opening_tag(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="<div>")
        result = expert.highlight(block)
        assert result.code == "<div>"
        assert result.tokens is not None
        tag_tokens = [t for t in result.tokens if t.type == "tag"]
        assert len(tag_tokens) == 1

    def test_highlight_closing_tag(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="</div>")
        result = expert.highlight(block)
        assert result.code == "</div>"
        assert result.tokens is not None
        tag_tokens = [t for t in result.tokens if t.type == "tag"]
        assert len(tag_tokens) == 1

    def test_highlight_self_closing_tag(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="<br/>")
        result = expert.highlight(block)
        assert result.code == "<br/>"
        assert result.tokens is not None
        tag_tokens = [t for t in result.tokens if t.type == "tag"]
        assert len(tag_tokens) == 1

    def test_highlight_string_double_quote(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code='"hello"')
        result = expert.highlight(block)
        assert result.code == '"hello"'
        assert result.tokens is not None
        string_tokens = [t for t in result.tokens if t.type == "string"]
        assert len(string_tokens) == 1

    def test_highlight_string_single_quote(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="'hello'")
        result = expert.highlight(block)
        assert result.code == "'hello'"
        assert result.tokens is not None
        string_tokens = [t for t in result.tokens if t.type == "string"]
        assert len(string_tokens) == 1

    def test_highlight_entity(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="&nbsp;")
        result = expert.highlight(block)
        assert result.code == "&nbsp;"
        assert result.tokens is not None
        keyword_tokens = [t for t in result.tokens if t.type == "keyword"]
        assert len(keyword_tokens) == 1

    def test_highlight_numeric_entity(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="&#65;")
        result = expert.highlight(block)
        assert result.code == "&#65;"
        assert result.tokens is not None

    def test_highlight_hex_entity(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="&#x41;")
        result = expert.highlight(block)
        assert result.code == "&#x41;"
        assert result.tokens is not None

    def test_highlight_operator(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code="=")
        result = expert.highlight(block)
        assert result.code == "="
        assert result.tokens is not None
        operator_tokens = [t for t in result.tokens if t.type == "operator"]
        assert len(operator_tokens) == 1

    def test_highlight_full_document(self):
        expert = XmlHighlighterExpert()
        block = HighlightBlock(code='<root><child attr="value">text</child></root>')
        result = expert.highlight(block)
        assert result.code == '<root><child attr="value">text</child></root>'
        assert result.tokens is not None
