# Publishing `ratctl` to Hugging Face 🤗

This guide explains how to publish `ratctl` to Hugging Face across three surfaces:
1. **Interactive Space** (Live browser auditor for verifiers & reward functions)
2. **Benchmark Dataset** (The 112 audited RL environments with labels & exploit traces)
3. **Paper Submission** (Linking `PAPER.md` to Hugging Face Papers)

---

## 1. Deploy the Interactive Hugging Face Space

The repository includes a ready-to-deploy Hugging Face Space in the `hf_space/` directory using Gradio and the `ratctl` engine.

### Method A: Via Git (Fastest)

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Set Space Name: `ratctl-verifier-auditor` (or your preferred name).
3. Select **SDK: Gradio** and **License: MIT**.
4. Clone your new Space locally:
   ```bash
   git clone https://huggingface.co/spaces/<your-hf-username>/ratctl-verifier-auditor
   cd ratctl-verifier-auditor
   ```
5. Copy the files from `hf_space/` and the `ratctl/` core engine:
   ```bash
   # Copy space config and code
   cp -r /path/to/ratctl/hf_space/* .
   cp -r /path/to/ratctl/ratctl .
   ```
6. Commit and push:
   ```bash
   git add .
   git commit -m "feat: launch ratctl interactive verifier auditor Space"
   git push
   ```
7. Your Space will build and be live at `https://huggingface.co/spaces/<your-hf-username>/ratctl-verifier-auditor`!

### Method B: Via `huggingface_hub` CLI

```bash
pip install huggingface_hub
huggingface-cli login

# Upload the space directory directly
huggingface-cli upload-space <your-hf-username>/ratctl-verifier-auditor ./hf_space
```

---

## 2. Publish the 112-Environment Security Benchmark Dataset

To publish the empirical evaluation dataset to Hugging Face Datasets:

1. Create a dataset repo at [huggingface.co/new-dataset](https://huggingface.co/new-dataset) named `reward-hackability-112`.
2. Push `benchmarks/` and `AUDIT_REPORT.md` metadata:
   ```python
   from datasets import Dataset, DatasetDict
   import json

   # Load audit summary
   with open("AUDIT_REPORT.md", "r") as f:
       summary = f.read()

   # Push dataset
   # Columns: env_name, format, gameability_score, findings, vulnerable
   ```

---

## 3. Link `PAPER.md` to Hugging Face Daily Papers

Once published as an arXiv preprint or OpenReview submission, claim and link the paper on [Hugging Face Papers](https://huggingface.co/papers) to allow the open-source RL community to discuss and evaluate verifier hackability directly.
