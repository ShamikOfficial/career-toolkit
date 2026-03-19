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

Dependencies are:

- `streamlit` – web UI framework
- `fpdf2` – PDF generation

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

ollama pull qwen2.5:7b-instruct