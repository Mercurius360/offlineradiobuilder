"""
Text templates for the .sii files this app writes.

Stage 1 only needs manifest.sii and an (initially empty) offline_radio
container file. Station block generation is added in a later stage.
"""

from constants import escape_sii_string


def build_manifest_sii(display_name: str, author: str, *, has_icon: bool = True) -> str:
    """
    Build manifest.sii content matching the required template. The `icon`
    line is only included when has_icon is True -- claiming an icon file
    that was never actually saved produces "Cannot find mod icon" in-game.
    """
    icon_line = '\ticon: "mod_icon.jpg"\n' if has_icon else ""
    return (
        "SiiNunit\n"
        "{\n"
        "mod_package : .package_name\n"
        "{\n"
        '\tpackage_version: "1.0"\n'
        f'\tdisplay_name: "{escape_sii_string(display_name)}"\n'
        f'\tauthor: "{escape_sii_string(author)}"\n'
        "\tmp_mod_optional:\ttrue\n"
        '\tcategory[]: "sound"\n'
        '\tcategory[]: "ui"\n'
        f"{icon_line}"
        '\tdescription_file: "mod_description.txt"\n'
        "}\n"
        "}\n"
    )


def build_empty_radio_sii() -> str:
    """
    Initial contents of offline_radio.[mod].sii before any stations exist.
    Station blocks get inserted inside this SiiNunit {} body in a later stage.
    """
    return "SiiNunit\n{\n\n}\n"
