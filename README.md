# NaturalLanguage2Automation: NL to Browser Automation 🦅

**NaturalLanguage2Automation** is a next-generation automation testing tool that eliminates the need for brittle testing scripts. It uses a **"Brain-First"** approach, where a multimodal LLM directly controls a browser via the Chrome DevTools Protocol (CDP).

> [!IMPORTANT]
> **API Key Setup Required:** To use this project, you must have a Gemini API Key. Paste your key into `backend/.env` as `GEMINI_API_KEY=your_key_here`.

---

## 🧠 How It Works: The "Sense-Think-Act" Loop

Unlike traditional tools (Selenium, Playwright scripts) that follow a fixed set of instructions, NaturalLanguage2Automation operates in a continuous, live loop:

1.  **SENSE (Observation)**:
    -   The system captures a **Screenshot** of the current page.
    -   It extracts the **Accessibility Tree (AXTree)** via CDP to understand the semantic structure (buttons, inputs, roles).
    -   It listens for **Console Logs** and **Network Errors** in real-time.
2.  **THINK (Reasoning)**:
    -   The **AgentCore** (Gemini AI) analyzes the visual state and AXTree.
    -   It uses **State-Target-Goal** reasoning:
        -   *State*: What is visible now?
        -   *Target*: What is the immediate milestone?
        -   *Goal*: How does this lead to the final objective?
    -   It identifies components by their protocol-level `nodeId` instead of risky CSS selectors.
3.  **ACT (Interaction)**:
    -   The **BrowserService** sends zero-script commands directly through CDP.
    -   Instead of `page.click(".some-brittle-class")`, it calculates the exact **Coordinates** of a `nodeId` and dispatches a hardware-level click.

---

## 🚀 Key Features

-   **Protocol-First Architecture**: No Python/JS scripts are generated. The AI talks directly to the browser "body" via CDP.
-   **Chain-of-Thought Logging**: Full transparency into the AI's planning and reasoning steps.
-   **Infinite Loop Protection**: Automatic detection of repetitive actions with self-correction or fail-safe stops.
-   **Step-by-Step Mode**: Human-in-the-loop control to approve or pause every action.
-   **Visual Debugging**: Target elements are highlighted with purple outlines before interaction.

---

## 🛠️ Tech Stack

-   **Backend**: FastAPI, Playwright (CDP integration), Python.
-   **Frontend**: React (Vite), WebSockets.
-   **Intelligence**: Google Gemini (Multimodal Pro & Flash models).

---

## 📖 Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js
- **Gemini API Key** (You must paste your API key in `backend/.env`)

### 2. Configuration
Create/Update `backend/.env`:
```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

### 3. Launching the System

#### 🟢 Option A: Automatic (One-Click)
Run the batch script from the root directory:
```powershell
./start_app.bat
```

#### 🟡 Option B: Individual Terminals (Manual)

**Backend (API & AI Agent)**
- **Command Prompt (CMD)**:
  ```cmd
  cd backend
  python run_backend.py
  ```
- **PowerShell**:
  ```powershell
  cd backend
  python run_backend.py
  ```

**Frontend (UI)**
- **Command Prompt (CMD)**:
  ```cmd
  cd frontend
  npm run dev
  ```
- **PowerShell**:
  ```powershell
  cd frontend
  npm run dev
  ```

---

### 4. Running a Test
1.  Open `http://localhost:5173`.
2.  Type a goal like: `"Go to amazon.in and search for peanut butter"`.
3.  Click **Run Test**.
4.  Use the **Stop** button at any time to instantly kill the browser and save tokens.

---

## 🛡️ Stopping & Saving Tokens
- **Manual Stop (Inside UI)**: Click the red **Stop** button. This kills the current AI loop.
- **Full Shutdown (System Level)**: Run the `stop_app.bat` script in the root directory. This forcefully kills all backend, frontend, and lingering browser processes to ensure your system is clean.
- **Finished State**: Once the agent reaches "Goal Achieved!", it stops LLM calls automatically.
- **Smart Model Selection**: Uses faster models for repetitive execution and high-reasoning models for initial planning.
