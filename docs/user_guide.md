# ASIP User Guide & Operations Manual

Welcome to the **Autonomous Student Intelligence Platform (ASIP)**. This user manual guides you through using all 13 interactive views, managing course materials, running practice quizzes, tracking weaknesses, and executing autonomous multi-agent exam preparation.

---

## 1. Getting Started

### 1.1 First Launch
1. Ensure your dependencies are installed (`pip install -r requirements.txt`).
2. Run the application interface:
   ```bash
   streamlit run app.py
   ```
3. Open your browser at `http://localhost:8501`.

### 1.2 Setting Up Your Academic Profile
1. Navigate to **Student Profile** from the left sidebar.
2. Enter your Name, Degree/Course, Branch/Major, Academic Year, and Semester.
3. Set your target grade (e.g., A / 90%+) and available study hours per day.
4. Click **Save Profile**.

### 1.3 Registering a Subject & Syllabus
1. Navigate to **Subjects & Syllabus**.
2. Click **Create New Subject**.
3. Enter the Subject Name (e.g., `Python Programming`) and Course Code (`CS301`).
4. Add syllabus units and topic titles.

---

## 2. Managing Course Materials

Navigate to **Uploaded Materials**:
1. Select the target Subject from the dropdown.
2. Drag and drop your academic documents. ASIP accepts:
   - **PDFs (`.pdf`)**: Syllabi, textbook excerpts, lecture slides.
   - **Word Documents (`.docx`)**: Assignment sheets, term papers.
   - **Plain Text / Markdown (`.txt`, `.md`)**: Quick notes, cheat sheets.
   - **Spreadsheets (`.csv`)**: Exam score records, tabular datasets.
3. Click **Upload & Process Document**.
4. The system validates the file, extracts pages, chunks content into semantic sections, and updates the local TF-IDF vector index in `data/vector_store/`.
5. You can inspect indexed chunks or delete outdated documents anytime.

---

## 3. The 13 Navigation Views

| View Name | Core Functionality |
| :--- | :--- |
| **📊 Dashboard** | Overview of streak, completed tasks, readiness gauges, and quick actions. |
| **💬 AI Tutor** | Conversational chat with citations from your uploaded course notes. |
| **🎯 My Goals** | Academic goals manager with 1-click Autonomous Exam Prep launcher. |
| **📅 Study Planner** | Daily calendar timetable showing assigned tasks and completion checkboxes. |
| **📁 Uploaded Materials** | Document manager with multi-format indexing and chunk inspection. |
| **🧠 Knowledge Base** | Vector search playground to test semantic queries against your course notes. |
| **🤖 Agents & Execution Trace** | Live inspectability into agent reasoning, tool payloads, and critic scores. |
| **📝 Quizzes & Mock Exams** | Adaptive diagnostic tests and mock exams with instant grading and explanations. |
| **📈 Progress & Weaknesses** | Interactive Plotly visual charts of mastery curves, strengths, and priority gaps. |
| **📋 Readiness Reports** | Formal exam readiness evaluations downloadable as Markdown and HTML. |
| **👤 Student Profile** | Academic preferences, study hours, target grades, and personal details. |
| **📚 Subjects & Syllabus** | Course curriculum, units, and topic completion trackers. |
| **🔧 Developer & Diagnostics** | Telemetry, database tables, vector chunk count, and model diagnostics. |

---

## 4. Running the Primary Acceptance Test: Autonomous 7-Day Exam Prep

To experience the full autonomous capability of ASIP:

### Step 1: Upload Your Materials
1. Go to **Uploaded Materials**.
2. Upload your course syllabus file (e.g. `python_syllabus.txt`) and past question papers (`python_past_papers.txt`).

### Step 2: Launch Autonomous Exam Prep
1. Navigate to **My Goals**.
2. In the **Autonomous Exam Preparation** card, select the subject (`Python Programming`).
3. Enter the prompt:
   > *"Prepare me for my Python exam in 7 days. I have uploaded my syllabus and previous question papers."*
4. Click **Launch Autonomous Preparation**.

### Step 3: Observe the 15-Step Agent Loop
The system displays live progress as the AGI Controller coordinates:
1. Understanding your learning goal and time constraints.
2. Inspecting your uploaded materials and verifying syllabus coverage.
3. Discovering key curriculum topics and prerequisites.
4. Generating an initial day-by-day study schedule.
5. Delegating tasks across the `PlannerAgent`, `StudyAgent`, and `CodingAgent`.
6. Administering a diagnostic assessment.
7. Identifying detected weaknesses (e.g., Object-Oriented Programming).
8. Dynamically adapting the 7-day schedule to inject remedial tasks.
9. Producing targeted concept reviews and coding challenges.
10. Re-evaluating mastery via a follow-up test.
11. Saving sanitized memory preferences.
12. Generating an Exam Readiness Report.

### Step 4: Review Results
- Check the **Study Planner** to see your updated adaptive daily timetable.
- Visit **Agents & Execution Trace** to review every tool call, AST check, and agent decision.
- Visit **Readiness Reports** to download your personalized revision guide.

---

## 5. Safe Sandboxed Code & Math Practice

### Using the Python Sandbox
Inside the **AI Tutor** or during a coding study task:
1. Ask the tutor to demonstrate an algorithm:
   > *"Show me how a binary search tree works in Python and test it with sample inputs."*
2. The `CodingAgent` invokes `python_sandbox` to verify the code works before returning the answer.
3. Unsafe operations (such as trying to read local disk files or run shell commands) are automatically caught and blocked by the AST analyzer.

### Using the Math Calculator
1. Ask numerical or algebraic questions:
   > *"Calculate the eigenvalues of the matrix [[2, 1], [1, 2]] and show working."*
2. The `MathAgent` uses the strict AST `calculator` tool to verify numerical steps with zero risk of arithmetic hallucinations.

---

## 6. Personalization & Memory Management

Navigate to **Student Profile** or **Settings**:
- The platform automatically retains personal context (e.g., `"prefers code examples"`, `"struggles with recursion"`).
- Sensitive tokens like API keys (`AIza...`, `sk-...`) or passwords are automatically sanitized and never stored in long-term memory.
- You can inspect, modify, or delete any stored memory key at any time.

---

## 7. Troubleshooting & FAQ

### Q1: Can I use ASIP completely offline without internet or API keys?
**Yes.** ASIP contains a built-in `OfflineMockProvider` and pure-Python local TF-IDF vector engine. If no Gemini or OpenAI keys are configured in `.env`, the system functions smoothly without crashes.

### Q2: How do I enable Google Gemini 2.0?
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/).
2. Add your key to `.env`:
   ```ini
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_key_here
   ```
3. Restart Streamlit or FastAPI.

### Q3: How do I run tests?
Execute:
```bash
pytest -v
python verify_phase1.py
python verify_phase2.py
python verify_phase3.py
```
All 29 pytest suites and phase verification scripts will validate with zero errors.
