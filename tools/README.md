# tools — reusable InterLisp-D revival utilities

Small, dependency-light utilities written while reviving the 1986 HEARTS system
(see [../REVIVAL-LOG.md](../REVIVAL-LOG.md)). They are **not specific to HEARTS** —
they should help anyone bringing scanned or OCR'd InterLisp-D source back to life on
Medley Interlisp (https://interlisp.org/).

| Tool | What it does | Why you'll want it |
|---|---|---|
| `interlisp-lint.py` | Bracket linter that models `[ ]` super-bracket semantics and checks **each top-level form independently**. | OCR'd Interlisp source is full of `[`↔`(` slips. A *global* paren count hides them (one error's extra-close cancels another's missing-close). Per-form checking surfaces every broken definition and the exact line. |
| `interlisp-balance.py` | Whole-file bracket balance checker (super-bracket aware, handles `%` escapes, strings, `(* … )` comments, and `;;` / `#\|…\|#` transcription annotations). | Quick pass/fail on a whole file; used as a build sanity check. Use `interlisp-lint.py` to *localize* problems. |
| `readbitmap-decode.py` | Decodes/validates/renders an Interlisp `READBITMAP` "hardcopy" packed bitmap to a PNG. | Lets you *see* whether an OCR'd bitmap literal is actually the artwork it should be (a suit pip, an icon) before trusting it — and catches illegal characters that make `READBITMAP` fault. |

## Notes that generalize

- **The assignment arrow `←` is ASCII underscore `_` (code 95).** `←` is only the display
  glyph. Transcribe/keep it readable, but the byte the CLISP reader treats as assignment is `_`.
- **`READBITMAP` packing:** each char is a 4-bit nibble (`@`=0 … `O`=15, letters only),
  MSB-first, each scanline padded to a 16-bit word. So an 11-wide bitmap is 4 chars/row, a
  30-wide one is 8. Black suits were drawn solid; **red suits (♦♥) were dithered** to read as
  "gray" on a monochrome display.
- **Super-brackets:** `]` closes back to the nearest `[` (or to top level if none). This is the
  single biggest source of OCR-transcription bugs, because `[` and `(` look alike in a scan.

## Usage

```bash
python3 tools/interlisp-lint.py path/to/source.lisp
python3 tools/interlisp-balance.py path/to/source.lisp
python3 tools/readbitmap-decode.py Clubs 11 11 "@D@@" "@N@@" "AO@@" ...   # writes Clubs.png
```

`readbitmap-decode.py` needs Pillow for PNG output (`pip install pillow`); without it, it still
prints the ASCII-art rendering and the validation report.
