"""Small helpers shared by the tests."""

from app.pdf_text import Line


def make_lines(rows: list) -> list:
    """Build Line objects from strings, top to bottom. '||' separates segments.

    make_lines(["Invoice No: NW-1042", "Subtotal || 361.60"])
    """
    lines = []
    for index, row in enumerate(rows):
        segments = [part.strip() for part in row.split("||")]
        starts = [50.0 + 200.0 * i for i in range(len(segments))]
        lines.append(Line(text="    ".join(segments), segments=segments, starts=starts,
                          page=1, top=40.0 + 14.0 * index, x0=50.0))
    return lines