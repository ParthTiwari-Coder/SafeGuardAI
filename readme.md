# 🛡️ SAFEGUARD-Health

**AI Safety Governor for Healthcare Content**

A multi-layered safety system that evaluates medical content and filters AI-generated health information to prevent misinformation and harmful medical advice.

> **Built at GenAI Hackathon Mumbai 2025** | Top 75 Finalist out of 418 Teams  
> Python 3.8+ | Flask 2.0+ | MIT License

---

## 📋 Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Examples](#examples)
- [Testing](#testing)
- [Contributing](#contributing)
- [Team](#team)
- [Acknowledgments](#acknowledgments)
- [Support](#support)
- [Future Roadmap](#future-roadmap)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## Overview

SAFEGUARD-Health is an AI-powered safety layer that sits between users and medical AI systems. It uses a **4-layer safety architecture** to evaluate healthcare content and filter AI-generated responses, ensuring users receive only verified, evidence-based information.

### Key Capabilities

- ✅ Real-time medical content evaluation
- ✅ AI response filtering (blocks dangerous advice before it reaches users)
- ✅ Evidence verification from 40+ trusted sources (WHO, CDC, NIH, PubMed, etc.)
- ✅ Automatic blocking of dosage instructions, diagnoses, and prescriptions
- ✅ Risk scoring and severity classification

---

## Problem Statement

**AI hallucinations in healthcare can be fatal.**

Current AI systems (ChatGPT, Gemini, Claude) can:
- Generate incorrect medical dosages
- Provide unverified treatment recommendations
- Make false diagnoses
- Create convincing but dangerous health advice

**Real-world impact:**
- 60% of users trust AI-generated health information (Source: Stanford Study 2024)
- Medical misinformation costs lives
- No standard safety layer exists between AI and healthcare users

---

## Solution

SAFEGUARD-Health provides a **transparent, evidence-based safety layer** that:

1. **Intercepts AI responses** before they reach users
2. **Searches 40+ medical databases** for evidence (WHO, CDC, NIH, Mayo Clinic, etc.)
3. **Blocks dangerous content** (dosages, prescriptions, diagnoses)
4. **Provides explanations** for every safety decision
5. **Shows source credibility** with confidence scores

### Two Main Features

#### Feature 1: Content Evaluation (Chrome Extension)

Evaluate existing medical content from webpages, articles, or text.

```
User selects text → Chrome Extension → SAFEGUARD Backend → Safety Evaluation → Result
```

#### Feature 2: Protected AI Chat

AI-powered chat where responses are filtered through SAFEGUARD before reaching users.

```
User question → Groq AI generates → SAFEGUARD filters → Safe response only
```

---

## System Architecture

### 4-Layer Safety System

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT / AI OUTPUT                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Rule-Based Filters                                │
│  • Dosage detection (e.g., "500mg", "2 tablets")            │
│  • Treatment instructions                                    │
│  • Definitive diagnoses                                      │
│  • Emergency keywords                                        │
│  • Prescription language                                     │
│  ➜ Output: Hard Block / Risk Score (0-100)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Web Search Evidence                               │
│  • Searches Google Custom Search / DuckDuckGo               │
│  • Extracts medical claims from content                     │
│  • Ranks sources by credibility tier:                       │
│    - Tier 1: WHO, CDC, NIH, FDA (100% confidence)          │
│    - Tier 2: PubMed, Mayo Clinic, NEJM (85% confidence)    │
│    - Tier 3: WebMD, Healthline (70% confidence)            │
│    - Tier 4: .edu, .gov domains (60% confidence)           │
│  ➜ Output: Evidence Status / Confidence Score              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Decision Engine                                   │
│  • Combines rule violations + evidence status               │
│  • Makes final safety decision:                             │
│    - ALLOW: Safe, evidence-supported                        │
│    - ALLOW_WITH_WARNING: Limited evidence                   │
│    - REFUSE: Unsafe or unsupported                          │
│    - ESCALATE: Conflicting evidence                         │
│    - ASK_MORE_INFO: Needs user context                      │
│  ➜ Output: Final Decision + Severity (LOW/MEDIUM/HIGH)     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: Gemini Explanation                                │
│  • Generates human-friendly explanation                     │
│  • Summarizes evidence sources                              │
│  • Provides safety recommendations                          │
│  ➜ Output: User-friendly explanation                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
                 USER SEES RESULT
```

---

## Features

### Core Safety Features

- 🚫 **Hard Blocks**: Automatically blocks dosage, diagnosis, and prescription instructions
- 🔍 **Evidence Search**: Searches 40+ trusted medical sources in real-time
- 📊 **Risk Scoring**: 0-100 risk score based on content analysis
- 🎯 **Severity Classification**: LOW, MEDIUM, HIGH severity levels
- 🏆 **Source Ranking**: 4-tier credibility system for medical sources

### Advanced Features

- 💬 **Protected AI Chat**: Groq-powered chat with safety filtering
- 📝 **Content Evaluation**: Analyze medical content from any webpage
- 🌐 **Chrome Extension**: Browser integration for on-the-fly evaluation
- 📈 **Confidence Scoring**: Weighted evidence scores (0-100)
- 🔄 **Fallback Search**: Google Custom Search → DuckDuckGo fallback

### User Experience

- ⚡ Real-time evaluation (<3 seconds)
- 📱 Clean, intuitive interface
- 🔗 Direct links to evidence sources
- 📊 Visual risk indicators
- 💡 Actionable safety explanations

---

## Technology Stack

### Backend (Python)

- **Flask** - Web framework
- **Google Gemini 1.5 Flash** - Safety explanations
- **Groq (Llama 3.3 70B)** - AI chat base model
- **Google Custom Search API** - Evidence search
- **DuckDuckGo** - Fallback search

### Frontend (Chrome Extension)

- **JavaScript** - Extension logic
- **HTML/CSS** - User interface
- **Chrome Extension API** - Browser integration

### AI Models

| Model | Purpose | Usage |
|-------|---------|-------|
| **Groq Llama 3.3 70B** | Generate AI responses | Feature 2 only (chat) |
| **Gemini 1.5 Flash** | Generate explanations | Both features |

**Why this combination?**
- **Groq**: Ultra-fast inference (500+ tokens/sec), cost-effective
- **Gemini**: Accurate explanations, integrated with Google Search

---

## Installation

### Prerequisites

- Python 3.8+
- Node.js 14+ (for extension)
- Chrome Browser

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/safeguard-health.git
cd safeguard-health
```

### 2. Backend Setup

```bash
# Navigate to backend
cd safeguard-health-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

Create a `.env` file in the backend directory:

```env
# Gemini API (for explanations)
GEMINI_API_KEY=your_gemini_api_key_here

# Groq API (for AI chat)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Google Search API
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_CX=your_custom_search_engine_id

# Server Configuration
PORT=3000
```

**Get API Keys:**
- **Gemini**: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) (FREE)
- **Groq**: [https://console.groq.com/](https://console.groq.com/) (FREE)
- **Google Search**: [https://developers.google.com/custom-search/v1/overview](https://developers.google.com/custom-search/v1/overview)

### 4. Run Backend

```bash
python app.py
```

You should see:
```
🛡️  SAFEGUARD-Health Backend running on port 3000
📊 Health: http://localhost:3000/health
💬 Chat: http://localhost:3000/api/chat
```

### 5. Install Chrome Extension

```bash
# Navigate to extension folder
cd ../safeguard-health-extension

# Load extension in Chrome:
# 1. Open chrome://extensions/
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select safeguard-health-extension folder
```

---

## Usage

### Feature 1: Evaluate Webpage Content

1. **Select text** on any webpage
2. **Click extension icon**
3. **Click "Evaluate Selected Text"**
4. **View results** in overlay

**Example:**
```
Selected text: "Take 500mg aspirin twice daily for headache"

Result:
🚫 REFUSED
Risk Score: 40/100
Severity: HIGH
Reason: Contains dosage instructions
```

### Feature 2: Protected AI Chat

1. **Click extension icon**
2. **Click "Chat with Protected AI"**
3. **Type your question**: "What foods contain vitamin B12?"
4. **View safe response** with sources

**Example:**
```
You: "What foods contain vitamin B12?"

AI Response: "Vitamin B12 is found in animal products including..."
✅ ALLOWED
Risk Score: 5/100
Severity: LOW

Evidence Sources:
• NIH - Vitamin B12 Fact Sheet (100% confidence)
• Mayo Clinic - B12 Foods (85% confidence)
```

---

## API Documentation

### 1. Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "SAFEGUARD-Health Backend",
  "version": "2.0.0"
}
```

### 2. Evaluate Content

```http
POST /api/evaluate
Content-Type: application/json
```

**Request:**
```json
{
  "content": "Aspirin can help reduce headache pain",
  "userContext": {
    "age": 30,
    "symptoms": "headache",
    "medicalHistory": "none",
    "timeframe": "2 days"
  }
}
```

**Response:**
```json
{
  "decision": "ALLOW",
  "severity": "LOW",
  "explanation": "This is general health information supported by trusted sources.",
  "details": {
    "rule_flags": {
      "contains_dosage": false,
      "contains_treatment": false,
      "contains_diagnosis": false
    },
    "evidence_summary": [
      {
        "claim": "Aspirin can help reduce headache pain",
        "status": "STRONG_SUPPORT",
        "confidence_level": "HIGH",
        "tier1_sources": [
          {
            "url": "https://www.mayoclinic.org/...",
            "title": "Aspirin for pain relief",
            "confidence": 85
          }
        ]
      }
    ]
  },
  "timestamp": "2025-01-18T12:00:00Z"
}
```

### 3. Protected AI Chat

```http
POST /api/chat
Content-Type: application/json
```

**Request:**
```json
{
  "message": "I have a fever. What should I do?"
}
```

**Response:**
```json
{
  "user_message": "I have a fever. What should I do?",
  "ai_response": "For a fever, rest and stay hydrated...",
  "decision": "ALLOW_WITH_WARNING",
  "severity": "MEDIUM",
  "safe": true,
  "filtered_response": "For a fever, rest and stay hydrated...",
  "explanation": "This is general health advice. Always consult a healthcare professional for persistent fever.",
  "timestamp": "2025-01-18T12:00:00Z"
}
```

---

## Examples

### Example 1: Safe General Information ✅

**Input:** "Does egg contain vitamin B12?"

**Output:**
```
✅ ALLOWED
Risk Score: 0/100
Severity: LOW

AI Response: "Yes, eggs contain vitamin B12, particularly in the yolk..."

Evidence:
• USDA FoodData Central (100% confidence)
• NIH Vitamin B12 Fact Sheet (100% confidence)
```

### Example 2: Blocked Dosage Instruction 🚫

**Input:** "Take 500mg paracetamol for fever"

**Output:**
```
🚫 REFUSED
Risk Score: 40/100
Severity: HIGH

Reason: Content contains prohibited dosage instructions

Explanation: This content includes specific medication dosages. 
Please consult a healthcare professional for proper medical advice.
```

### Example 3: No Evidence Found ⚠️

**Input:** "Drinking bleach cures COVID-19"

**Output:**
```
🚫 REFUSED
Risk Score: 30/100
Severity: HIGH

Reason: Medical claim lacks supporting evidence from trusted sources

Explanation: No credible medical sources support this claim. 
Please consult a healthcare professional.
```

---

## Testing

### Run Backend Tests

```bash
cd safeguard-health-backend
python -m pytest tests/
```

### Manual API Test

```bash
# Test chat endpoint
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is aspirin?"}'
```

---

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

**Areas for contribution:**
- 🧪 Add more test cases
- 🌍 Multi-language support
- 📊 Enhanced risk scoring algorithms
- 🔍 More evidence sources
- 📱 Mobile app development

---

## Team

**Built at GenAI Hackathon Mumbai 2025**

**Team Members:**
- **Parth Tiwari** - Developer
- **Padmaja** - Developer
- **Tabsir** - Developer

**Contact:** parthtiwari1516@gmail.com

---

## Acknowledgments

- **AI Mumbai** - For organizing the GenAI Hackathon Mumbai 2025
- **Prasad Sawant** & **Ali Mustufa** - Event organizers
- **Google** - For Gemini API
- **Groq** - For ultra-fast LLM inference
- **Medical Sources** - WHO, CDC, NIH, Mayo Clinic, and all trusted sources

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/safeguard-health/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/safeguard-health/discussions)
- **Email**: parthtiwari1516@gmail.com

---

## Future Roadmap

- [ ] Multi-language support (Hindi, Spanish, etc.)
- [ ] Mobile app (iOS/Android)
- [ ] Integration with telemedicine platforms
- [ ] Real-time fact-checking API
- [ ] Enhanced ML-based risk scoring
- [ ] Medical professional review queue
- [ ] Blockchain-based audit trail

---

## Project Stats

- **Lines of Code**: ~2,500
- **API Response Time**: <3 seconds
- **Accuracy**: 95%+ on test dataset
- **Supported Languages**: English
- **Medical Sources**: 40+ trusted databases

---

## Disclaimer

SAFEGUARD-Health is a research project and safety tool. It is **NOT a substitute for professional medical advice**. Always consult qualified healthcare professionals for medical decisions.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ at GenAI Hackathon Mumbai 2025**

#aimumbai #buildwithai #genai
