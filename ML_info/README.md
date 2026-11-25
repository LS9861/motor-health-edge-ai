# ML documentation

Two companion documents, both generated from source in this folder.

| File | Pages | Audience | What it covers |
|------|-------|----------|----------------|
| `ML_Guide_for_Motor_Health.pdf` | 10 | Engineers | The build itself — sensor choice, feature selection, why a 1D CNN, training method, INT8 quantisation, TFLM deployment, and the voltage-shortcut case study. Project-specific. |
| `ML_Primer_for_Beginners.pdf` | 19 | Beginners | Machine learning from zero, taught with this project as the running example. 13 illustrations, two worked examples per chapter (one from this project, one everyday), and a glossary. |

The guide answers *"what did you build?"*. The primer answers *"how does this work, for someone who has never seen it?"* — the second one is the harder document to write.

## Regenerating

All scripts are self-contained; none depend on files outside this folder.

```bash
# 1. Primer illustrations (13 PNGs -> img/)
python ML_info/make_illustrations.py

# 2. The two PDFs
python ML_info/make_ml_primer_pdf.py
python ML_info/make_ml_guide_pdf.py
```

Both PDF scripts locate their output relative to themselves (`HERE`), so they can be
run from any working directory. Re-running only needs Python plus `reportlab`,
`matplotlib`, and `numpy`.

## Layout

```
ML_info/
├── ML_Guide_for_Motor_Health.pdf   <- generated
├── ML_Primer_for_Beginners.pdf     <- generated
├── make_ml_guide_pdf.py            <- ReportLab source (guide)
├── make_ml_primer_pdf.py           <- ReportLab source (primer)
├── make_illustrations.py           <- matplotlib source (diagrams)
└── img/                            <- generated PNGs used by the primer
```

> The generated PDFs and PNGs are committed so the documents are readable on GitHub
> without a local build. The `img/` PNGs are inputs to the primer, not artwork to edit
> by hand — change `make_illustrations.py` and re-run instead.
