# AI tools used

## Claude (Anthropic), claude.ai chat

I used Claude as a pair programmer for the whole assignment.

- **Design**: discussed the brief, the approach (rules instead of machine
  learning) and the project structure.
- **Code**: Claude drafted the modules in `app/`, the invoice generator,
  the evaluation scripts, the tests and `run.sh`. I ran, checked and
  debugged each part step by step.
- **Debugging**: when scores dropped, we collected evidence first
  (failure lists, breakdowns by label and layout, text dumps of single
  invoices) and fixed only what the evidence showed.
- **Documents**: first drafts of README.md, DATA.md and NOTES.md, which I
  reviewed and edited.

## My own decisions and checks

- Asked for wide anomaly coverage (watermarks, multi-page, round-off,
  bank footers, full-width digits and more) after the first generator.
- Required proof before every fix. Example: the "subtotal returned as
  total" bug was confirmed when expected ÷ returned matched each
  country's tax rate exactly.
- Kept the held-out group B honest: checked with `grep` that no group B
  wording was in the extractor, saved the blind score (75.6%) before any
  B-guided fix, and reported both numbers in DATA.md.
- Compared generated PDFs with their expected JSON by hand.
- Tested the project as a reviewer would, from a clean copy with a new
  virtual environment, before uploading.

No other AI tools were used.