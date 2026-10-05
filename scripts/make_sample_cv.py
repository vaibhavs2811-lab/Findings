"""Write data/sample_cv.pdf: a fictional one-page CV used by scripts/check_autofill.py --pdf."""

from __future__ import annotations

from pathlib import Path

LINES = [
    "Dr. Priya Raman",
    "Postdoctoral Researcher, Department of Sociology, Fictional State University",
    "",
    "EDUCATION",
    "PhD in Sociology, Fictional State University (2022)",
    "MA in Public Policy, Example College (2018)",
    "",
    "RESEARCH EXPERIENCE",
    "Led semi-structured interview studies on gig work and urban housing.",
    "Coded 120 interviews in NVivo and ran thematic analysis; mixed-methods survey design in R.",
    "",
    "INTERESTS: gig economy, urban housing, qualitative methods, survey design",
    "SKILLS: NVivo, R, interviewing, thematic analysis, grant writing",
    "LOOKING FOR: collaborators who can add quantitative modelling to housing studies",
]


def build() -> bytes:
    def esc(t: str) -> str:
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
    for line in LINES:
        stream.append(f"({esc(line)}) Tj T*")
    stream.append("ET")
    content = "\n".join(stream).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "data" / "sample_cv.pdf"
    target.write_bytes(build())
    print(f"wrote {target} ({target.stat().st_size} bytes)")
