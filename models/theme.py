from dataclasses import dataclass, fields

@dataclass
class ThemeModel:
    """
    Color palette for the application UI.
    """
    bg: str
    bg2: str
    bg3: str
    accent: str
    accent2: str
    danger: str
    warning: str
    fg: str
    fg2: str
    border: str

    @classmethod
    def from_dict(cls, data:dict) -> 'ThemeModel':
        """
        Creates a theme from a dictionary, falling back to
        default colors if keys are missing
        """
        return cls(
            bg=data.get("bg", "#0f1117"),
            bg2=data.get("bg2", "#181c26"),
            bg3=data.get("bg3", "#1f2433"),
            accent=data.get("accent", "#4f8ef7"),
            accent2=data.get("accent2", "#2ecc8f"),
            danger=data.get("danger", "#e05252"),
            warning=data.get("warning", "#f0a500"),
            fg=data.get("fg", "#d6dce8"),
            fg2=data.get("fg2", "#7a8499"),
            border=data.get("border", "#2a3045")
        )

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}