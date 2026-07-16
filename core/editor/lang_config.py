from core.language.highlighter import (
    JsonHighlighterExpert,
    LogHighlighterExpert,
    PythonHighlighterExpert,
    XmlHighlighterExpert,
    YamlHighlighterExpert,
)
from core.language.suggestion import PythonSuggestionExpert

HIGHLIGHT_TOKENS = {
    "keyword": {"foreground": "#569cd6"},
    "builtin": {"foreground": "#dcdcaa"},
    "string": {"foreground": "#ce9178"},
    "number": {"foreground": "#b5cea8"},
    "comment": {"foreground": "#6a9955"},
    "identifier": {"foreground": "#9cdcfe"},
    "operator": {"foreground": "#d4d4d4"},
    "punctuation": {"foreground": "#d4d4d4"},
    "function": {"foreground": "#dcdcaa"},
    "class": {"foreground": "#4ec9b0"},
    "struct": {"foreground": "#4ec9b0"},
    "preprocessor": {"foreground": "#9b9b9b"},
    "decorator": {"foreground": "#dcdcaa"},
    "self": {"foreground": "#569cd6"},
    "type": {"foreground": "#4ec9b0"},
    "module": {"foreground": "#4fc1ff"},
    "key": {"foreground": "#9cdcfe"},
    "tag": {"foreground": "#569cd6"},
    "timestamp": {"foreground": "#6a9955"},
    "level_debug": {"foreground": "#808080"},
    "level_info": {"foreground": "#4ec9b0"},
    "level_warn": {"foreground": "#dcdcaa"},
    "level_error": {"foreground": "#f44747"},
    "level_critical": {"foreground": "#ff0000"},
}

LANG_CONFIG = {
    "Python": {
        "ext": ".py",
        "highlighter": PythonHighlighterExpert,
        "suggestion": PythonSuggestionExpert,
        "suggestion_factory": lambda: PythonSuggestionExpert(),
        "sample": 'def hello():\n    print("Hello, world!")\n\nhello()\n',
    },
    "JSON": {
        "ext": ".json",
        "highlighter": JsonHighlighterExpert,
        "suggestion": None,
        "suggestion_factory": lambda: None,
        "sample": '{\n  "name": "Alice",\n  "age": 30,\n  "city": "New York",\n  "active": true,\n  "data": null\n}\n',
    },
    "XML": {
        "ext": ".xml",
        "highlighter": XmlHighlighterExpert,
        "suggestion": None,
        "suggestion_factory": lambda: None,
        "sample": '<?xml version="1.0"?>\n<root>\n  <person id="1">\n    <name>Alice</name>\n    <age>30</age>\n  </person>\n</root>\n',
    },
    "YAML": {
        "ext": ".yaml",
        "highlighter": YamlHighlighterExpert,
        "suggestion": None,
        "suggestion_factory": lambda: None,
        "sample": '# Configuration file\nserver:\n  host: "localhost"\n  port: 8080\n  debug: true\n\ndatabase:\n  url: "postgres://localhost/mydb"\n  pool_size: 10\n',
    },
    "LOG": {
        "ext": ".log",
        "highlighter": LogHighlighterExpert,
        "suggestion": None,
        "suggestion_factory": lambda: None,
        "sample": "2024-01-15 10:30:45,123 INFO  Server started on port 8080\n2024-01-15 10:30:46,002 DEBUG Initializing database connection...\n2024-01-15 10:30:46,150 WARN  Configuration file not found, using defaults\n2024-01-15 10:30:47,890 ERROR Failed to connect to database: timeout\n2024-01-15 10:30:48,001 CRITICAL Application crashed\n",
    },
}

THEME_NAMES = ["Dark", "Light", "Solarized Dark"]
FONT_FAMILIES = ["Consolas", "Courier New", "Menlo", "Monaco"]
FONT_SIZES = [9, 10, 11, 12, 14, 16]
TAB_WIDTHS = [2, 4, 8]
