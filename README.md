## Resume Builder (Streamlit)

Interactive Streamlit app to generate a tailored resume PDF (`resume_YYYYMMDD_HHMMSS.pdf`) based on:

- **Target role / template**
- **Job description** (pasted or `.txt` upload)
- **Extra keywords**
- **Project selection** (auto or manual)

PDFs are saved to the `processed` folder and can also be downloaded directly from the UI.

---

### 1. Create & activate a virtual environment

From the project root (`Career_automations`), run:

```bash
# Create virtual environment (Windows, using venv)
python -m venv .venv

# Activate (PowerShell)
.venv\Scripts\Activate.ps1

# OR, if using cmd
.venv\Scripts\activate.bat
```

To deactivate later:

```bash
deactivate
```

---

### 2. Install dependencies

With the virtual environment active:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Dependencies include:

- `streamlit` – web UI framework
- `fpdf2` – PDF generation
- `playwright` – browser automation for the Job Apply Agent
- `requests` – local Ollama HTTP calls

---

### 3. Run the Streamlit app

From the project root:

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (typically `http://localhost:8501`).

---

### 4. Using the app

- Select **target role** in the sidebar.
- Paste or upload the **job description**.
- Add optional **extra keywords** (comma-separated).
- Optionally override the **summary**.
- Review and tweak **Experience**, **Education**, and **Skills**.
- Let the app auto-select projects or choose them manually.
- Click **“Build tailored resume PDF”**.

The generated file will be saved under:

- `processed/resume_YYYYMMDD_HHMMSS.pdf`

and is also available via the **Download PDF** button.

---

## Ollama (local AI)

Install Ollama and pull at least one model:

```bash
ollama pull qwen2.5:7b-instruct
```

Faster/lighter alternatives:

```bash
ollama pull qwen2.5:3b-instruct
# or
ollama pull llama3.2:3b-instruct
```

---

## Cover Letter Generator (local Ollama)

In the sidebar, choose **Cover Letter Generator**, paste a job description, and generate/edit/download a `.txt` cover letter.

---

## Job Apply Agent (Playwright + local Ollama)

This is a **semi-auto** browser assistant:
- Opens a real browser window (so you can complete **login** and **CAPTCHA** manually)
- Scans the current page for form fields
- Uses **one** local LLM call to generate answers for the whole page
- Fills what it can deterministically and skips unknowns as `__NEEDS_USER__`

### One-time Playwright browser install (local)

After installing Python deps:

```bash
python -m playwright install chromium
```

### Using the agent

1. Start the app: `streamlit run app.py`
2. In the sidebar choose **Job Apply Agent**
3. Paste the application URL and click **Open browser**
4. Complete any login/CAPTCHA in the browser window
5. Click **Scan current page** → then **Fill this page**

### Limitations
- Login and CAPTCHA are manual by design.
- “Any site” is best-effort; Greenhouse/Lever detection exists but many layouts will still need user review.

---

## Tests

Run the small unit tests:

```bash
python -m unittest discover -s tests
```