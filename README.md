# 🩺 Prose Clinic

An editorial assistant for fiction. It spots unnatural, formulaic, over-polished or repetitive
writing habits, the kind that make AI-generated prose feel generic, and helps you revise towards
prose that feels human, varied, character-driven and deliberate.

- **Rule-based analysis** (45 checks) runs entirely on your computer, with no internet and no account.
- **Optional AI critic and rewriter**: connect Claude, OpenAI, or a free local model (Ollama, LM Studio).
- **Your original text is never changed.** Suggestions go into a separate draft, shown side by side.

> It flags *possible* problems, not errors. A device used once on purpose is a choice; the same device
> everywhere is a habit. Most checks only fire when something is repeated or dense, and you can mark
> anything as a false positive. It is **not** an AI detector.

---

## 1. Install and start (first time)

You need to do steps 1 and 2 only once.

### Step 1: Install Python (version 3.11 or newer)

1. Go to <https://www.python.org/downloads/> and click the big yellow **Download Python 3.x** button.
2. Run the installer.
   - **Windows:** on the first screen, **tick "Add python.exe to PATH"**, then click **Install Now**.
   - **Mac:** click through the installer with the default options.
   - **Linux:** Python is usually installed already. Check with `python3 --version` in a terminal.

### Step 2: Get Prose Clinic onto your computer

- On the project's GitHub page, click the green **Code** button → **Download ZIP**.
- Unzip it somewhere easy to find, such as your **Documents** folder. You'll get a folder called
  `prose-clinic` (possibly with a suffix, like `prose-clinic-main`).

### Step 3: Start the app

Open the `prose-clinic` folder and:

- **Windows:** double-click **`start_windows.bat`**.
  If a blue "Windows protected your PC" box appears, click **More info** → **Run anyway**.
- **Mac:** right-click **`start_mac_linux.command`** → **Open** → **Open**. (Right-click is only needed
  the first time; after that you can double-click it.)
- **Linux:** open a terminal in the folder and run `bash start_mac_linux.command`.

The **first** start takes a minute or two, because it downloads the packages the app needs (this is the only
time it needs the internet). Then your web browser opens at **http://localhost:8501** with the app.
The app runs only on your computer; "localhost" means "this machine".

**To stop the app**, close the black/white terminal window that opened. **To start it again**, double-click
the same file; it starts in a few seconds from then on.

<details>
<summary><b>If the start file doesn't work: start it by typing commands instead</b></summary>

Open a terminal (**Windows:** press the Windows key, type `cmd`, press Enter. **Mac:** press Cmd+Space, type
`Terminal`, press Enter), then type these lines one at a time, pressing Enter after each. Replace the folder
path with wherever you unzipped the app.

**Windows**

```bat
cd %USERPROFILE%\Documents\prose-clinic
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

**Mac / Linux**

```bash
cd ~/Documents/prose-clinic
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Next time you only need the `cd …` line and the last line.
</details>

---

## 2. How to use it

The menu on the left has five sections.

### 🔍 Analyze
1. Paste a passage (a scene, a chapter, or a few paragraphs) into the box and click **Analyze**.
   Not sure where to start? Click **Load example** for a deliberately AI-flavoured passage.
2. On the left you see **your text with highlights**. Hover over a highlight to see what it's about; the small
   numbers match the numbered cards on the right. Short phrases are shaded; whole-sentence issues are underlined.
3. On the right, each **card** shows the issue type, the passage in context, a short explanation, and a
   suggested improvement. Use the filters to show only some categories or severities
   (🔺 likely issue, 🔸 worth a look, 🔹 minor/maybe).
4. On each card:
   - **👍 Useful / 🚫 False positive** records your verdict. False positives are hidden from now on (the same
     check flagging the same words) and can be restored any time.
   - **Add to revision list** collects the finding for the Revise page.
5. Other tabs: **🤖 AI critique** (optional, see section 3) and **📊 Statistics** (sentence-length chart,
   favourite sentence openers, and per-speaker dialogue statistics).

### ✏️ Revise
Your original is never modified. Everything here works on a separate **revision draft**.
- **Selected findings:** for each finding you collected, click **Suggest rewrite** (AI) to get two alternative
  rewrites, shown next to the original. Simple redundancies ("nodded her head") also have an offline
  **Apply quick fix** button. Each AI suggestion is re-checked by the rules: if it sneaks in a new cliché or AI
  habit, you get a warning before you apply it. Click **Apply to draft** to use one.
- **Full-passage revision** (AI): choose how much should change (light / moderate / thorough), which problems
  to address, and add your own instructions (e.g. *"Keep Mara's dry humour"*). The revision is shown side by
  side with your original (removed words struck through, new words highlighted), with a before/after count of
  flagged patterns and a list of any **new** problems the revision introduced. Nothing is applied until you
  click **Use as my revision draft**.
- **Revision draft:** edit the draft freely, compare it with the original side by side, **Re-check draft**,
  and **Download** it as a text file for your word processor.

### 📚 Style library (used only by the optional AI)
- **Style notes:** describe your voice and deliberate choices (*"First person present. I use fragments on
  purpose in fight scenes. Theo swears constantly."*) so they don't get "fixed" away.
- **Writing samples:** passages that sound the way you want to sound (150–400 words each works best).
- **Before → after examples:** weak prose next to the version you prefer. You can also save these straight
  from the Revise page with **Save as example**.

### ⚙️ Settings
- **Detection rules:** switch any of the 45 checks on or off and set **sensitivity** (high flags more,
  low only clear, repeated patterns). The 👍/🚫 counts beside each check show which ones work for you.
- **Custom phrases:** add your own pet hates. Plain text matches the phrase (`orbs`); `*` stands for one to
  four words (`not * but *`); experts can write regular expressions starting with `re:`. There's a box to test
  your list on sample text.
- **Feedback:** see and restore hidden findings, or clear all feedback.
- **AI connection:** choose and test an AI provider (section 3).
- **Backup:** download all settings, phrases, library and feedback as one file, or restore from one.

### ❓ Help
A summary of all of the above inside the app, plus a list of every check.

---

## 3. Optional: AI features

Everything above works without AI. AI adds a subjective second opinion (does this dialogue sound like a real
person? do these two characters sound alike?), rewrite suggestions, and full-passage revision.
When you use an AI feature, the passage (and your style library and feedback, unless you switch that off in
Settings) is sent to the provider you choose.

### Option A: Claude (Anthropic), pay-as-you-go
1. Create an account and an API key at <https://console.anthropic.com> (API use is billed per request,
   separately from any Claude.ai subscription).
2. In the `prose-clinic/.streamlit` folder, **copy** `secrets.toml.example` and name the copy `secrets.toml`.
   Open it in a text editor (Notepad, TextEdit) and paste your key between the quotes:
   `ANTHROPIC_API_KEY = "sk-ant-…"`. Save, then restart the app.
3. In the app, open **Settings → AI connection**, choose **Anthropic (Claude)**, and click **Test connection**.

The default model is `claude-opus-5-5` (most capable). For lower cost, type `claude-sonnet-5-5` or
`claude-haiku-5-5` into the Model box. **Effort** trades speed and cost for care; *high* is the default.

### Option B: free and private, with a local model (Ollama)
1. Install Ollama from <https://ollama.com> and start it.
2. In a terminal, download a model: `ollama pull llama3.1` (bigger models give better critiques but need a
   more powerful computer).
3. In **Settings → AI connection**, choose **OpenAI-compatible**, pick **Ollama** under *Quick setup*, make sure
   the model name matches what you pulled, and click **Test connection**.

Nothing leaves your computer with this option. LM Studio works the same way (preset **LM Studio**).

### Option C: OpenAI, OpenRouter or another OpenAI-compatible service
Choose **OpenAI-compatible**, pick the preset (or type the service's base URL and model name), and put your key
in `.streamlit/secrets.toml` as `OPENAI_API_KEY = "…"`.

### How your keys are kept safe
- The app **never writes API keys** into its own files. Keys come from `.streamlit/secrets.toml`, from an
  environment variable (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`), or from the "paste a key for this session only"
  box, which keeps it in memory until you close the app.
- `secrets.toml` is excluded from Git (`.gitignore`), so it isn't uploaded if you ever publish your copy.
- Backups never include keys.

---

## 4. Where your things are saved

Everything is saved automatically in the **`user_data`** folder inside `prose-clinic`:

| File | Contents |
|---|---|
| `settings.json` | which checks are on, sensitivities, custom phrases, AI choices (never keys) |
| `library.json` | style notes, writing samples, before → after examples |
| `feedback.json` | your 👍 / 🚫 verdicts |
| `drafts/` | archived revision drafts (kept whenever a draft is replaced) |

To move to a new computer, use **Settings → Backup**, or copy the `user_data` folder.
Pasted passages are not saved automatically; download your revision draft when you're done.

---

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| "Python 3.11 or newer was not found" | Install Python (step 1). On Windows, re-run the installer, choose *Modify*, and make sure "Add Python to environment variables" is ticked. |
| The browser didn't open | Open <http://localhost:8501> yourself. |
| "Port 8501 is in use" | The app is probably already running in another window. Close that window, or use the address it printed (e.g. `:8502`). |
| Package installation failed | Check your internet connection and start again; the launcher retries automatically. |
| AI: "rejected the API key" | Check for typos or stray spaces in `secrets.toml`, then restart the app. |
| AI: "Couldn't connect to http://localhost:11434" | Ollama isn't running. Start the Ollama app and try again. |
| AI: request rejected after changing the model | Set **Effort** to *default* in Settings (some older models don't support it). |
| Something looks wrong after an update | Delete the `.venv` folder inside `prose-clinic` and start again; it reinstalls cleanly. |

---

## 6. For the curious: how it works

```
app.py                      the Streamlit app (menu + page wiring)
prose_clinic/
  text.py                   splits text into paragraphs, sentences, words, dialogue; guesses speakers
  rules/                    the 45 checks, grouped by category (base.py explains how rules work)
  analyzer.py               runs the enabled checks and collects findings
  llm.py                    optional AI connections (Anthropic SDK, or OpenAI-compatible HTTP)
  ai_tasks.py               AI critic, rewrites, full revision, and the rule-based re-check of AI output
  highlight.py              highlighted text and side-by-side diffs
  storage.py                saving settings, library and feedback as JSON
  ui/                       one file per page
tests/                      automated tests (run with: python -m pytest)
```

### Adding your own check

Write a class in any file in `prose_clinic/rules/` and decorate it with `@register`. It appears in Settings
automatically. The simplest kind is a list of regular expressions:

```python
from .base import Pattern, PatternRule, register

@register
class Suddenly(PatternRule):
    id = "suddenly"
    name = "“Suddenly”"
    category = "cliche"   # formulaic, repetition, punctuation, purple, cliche, dialogue, emotion, conflict
    description = "The word “suddenly”, which rarely makes anything feel sudden."
    message = "“Suddenly” announces surprise instead of creating it."
    suggestion = "Cut it and let the abrupt event speak for itself."
    patterns = (Pattern(r"\bsuddenly\b"),)
```

For checks that need logic (counting, comparing sentences), subclass `Rule` and implement
`check(self, doc, ctx)`; see `rules/base.py` and the existing modules for examples. Run the tests with:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

(On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.)

### Technical notes
- Rule-based analysis uses only the Python standard library plus Streamlit for the interface; it never touches
  the network. Streamlit's anonymous usage statistics are switched off in `.streamlit/config.toml`, and the app
  only accepts connections from your own computer.
- Claude requests use the official `anthropic` package with streaming and structured (JSON) output. For models
  that support it, server-side refusal fallback is enabled, so if Claude's safety filter declines a request
  (rare for fiction editing), the request is retried on a fallback model instead of failing.
- OpenAI-compatible servers are called with plain HTTP (`requests`), so no extra SDK is needed for Ollama,
  LM Studio, OpenAI or OpenRouter.
