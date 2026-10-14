"""Print the text lines the extractor sees in one or more PDFs.

Usage:
    python -m eval.show data_gen/output/A/A_0001.pdf
"""

import sys
from pathlib import Path

from app.pdf_text import read_pdf


def main() -> None:
    # Always print UTF-8, so Japanese text works even when piped (| head, | tee).
    sys.stdout.reconfigure(encoding="utf-8")
    for name in sys.argv[1:]:
        text = read_pdf(Path(name).read_bytes())
        print(f"== {name}   pages={text.page_count}  chars={text.char_count}")
        for line in text.lines:
            print(f"p{line.page} {line.top:6.1f} | {' || '.join(line.segments)}")
        print()


if __name__ == "__main__":
    main()