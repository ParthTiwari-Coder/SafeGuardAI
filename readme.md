Browser (Chrome Extension)
↓
Content Capture (Text / Prompt)
↓
Backend API (app.py)
↓
Base LLM (Gemini API)
↓
4-Layer Safety Evaluation
↓
Filtered / Blocked Response
↓
Shown to User


---

## 🔐 Safety Design (Core Innovation)

All medical content passes through **four safety layers**:

1. **Rule-Based Filters**
   - Detects dosage instructions
   - Detects diagnosis and treatment claims
   - Flags actionable medical advice

2. **Medical Risk Classification**
   - Identifies high-risk vs low-risk content
   - Detects emergency or clinical scenarios

3. **Evidence Validation**
   - Flags unsupported or false medical claims
   - Prevents hallucinated medical facts

4. **Final Decision Engine**
   - Decides: Allow / Warn / Block
   - Generates user-safe explanations

⚠️ **The user NEVER sees raw AI output**

---

## 📁 Project Structure



safeai/
│
├── safeguard-health-backend/
│ ├── app.py # Backend API server
│ ├── requirements.txt # Python dependencies
│ ├── .env # API keys (not committed)
│ ├── test_api.py # API tests
│ └── venv/ # Virtual environment
│
├── safeguard-health-extension/
│ ├── manifest.json # Chrome extension config
│ ├── popup.html # Extension popup UI
│ ├── popup.js
│ ├── content.js # Webpage text capture
│ ├── background.js
│ ├── sidepanel.html # Protected AI chat UI
│ ├── sidepanel.js
│ ├── sidepanel.css
│ └── icons/
│
└── README.md


---

## 🚀 How to Run the Project (Local Setup)

### Step 1: Start the Backend

```bash
cd safeguard-health-backend
python app.py


Expected output:

🛡️ SAFEGUARD-Health Backend running on port 3000
📊 Health check: http://localhost:3000/health
💬 Chat endpoint: http://localhost:3000/api/chat


⚠️ The backend must be running before using the extension.

Step 2: Load the Chrome Extension

Open Google Chrome

Go to chrome://extensions

Enable Developer Mode

Click Load Unpacked

Select the folder:

safeguard-health-extension/


The extension will appear in the Chrome toolbar

🧪 How to Use
🔹 Feature 1: Evaluate Web Content

Select text on any webpage

Click the SAFEGUARD extension icon

Click Evaluate Selected Text

View safety analysis overlay on the page

🔹 Feature 2: Protected AI Chat

Click the SAFEGUARD extension icon

Click 💬 Chat with Protected AI

A side panel opens

Ask a medical question

AI generates → SAFEGUARD filters → Safe result shown

Example
User: How much aspirin should I take?
AI (raw): Take 500mg twice daily
SAFEGUARD: ❌ BLOCKED
User sees: "This response was blocked due to unsafe medical dosage advice."

💾 Data & Privacy

❌ No database

❌ No permanent storage

✅ Chat history exists only during the session

✅ When the side panel closes, all messages are cleared

🧠 Technologies Used

Python (Backend API)

Google Gemini API (Base LLM)

Chrome Extension (Manifest V3)

JavaScript, HTML, CSS

Rule-based + LLM-based safety logic

🎯 Project Goals

Prevent unsafe medical AI outputs

Demonstrate responsible AI deployment

Act as a safety governor, not a medical assistant

Suitable for real-world clinical AI pipelines

⚠️ Disclaimer

SAFEGUARD-Health does not provide medical advice.
It is a safety evaluation system designed to reduce risks from AI-generated medical content.
Thank you for reviewing our project.
We appreciate your time, attention, and valuable consideration of SAFEGUARD-Health.
Your feedback and insights mean a lot to us and help us move closer to building safer, more responsible AI systems in healthcare.