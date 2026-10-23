# YatraSathi – Context-Aware Conversational AI for Intelligent Travel Planning and Smart Tourism

YatraSathi is an AI travel companion for **Karnataka**. Travellers can chat (text or voice) in
**English, Kannada or Hindi**, get **personalised destination recommendations**, generate
**budget-optimised day-wise itineraries** with cost estimates, and read **RAG-grounded** tourism
information and stories about **62 tourist places**. An **admin panel** manages destinations,
users, itineraries, feedback and the AI knowledge base.

Built with **Python (Flask) + SQLite + scikit-learn + NLTK + pandas**. It runs fully offline with
demo data; an OpenAI key is optional.

---

## 1. Run it in VS Code (Windows)

1. Install **Python 3.10 – 3.13** from python.org (tick *“Add Python to PATH”*).
2. Unzip the project and open the `YatraSathi` folder in VS Code (**File → Open Folder**).
3. Open a terminal (**Terminal → New Terminal**, PowerShell) and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python app.py
```

4. Open **http://127.0.0.1:5000** in Chrome or Edge.

The first start creates `instance/yatrasathi.db` and loads the dataset plus demo data
(≈10–15 seconds). Later starts take about 2 seconds.

You can also double-click **`run.bat`**, or press **F5** in VS Code (*Run YatraSathi*
configuration in `.vscode/launch.json`).

### Demo accounts

| Role      | Email                     | Password |
|-----------|---------------------------|----------|
| Traveller | aishwarya@yatrasathi.in   | user123  |
| Admin     | admin@yatrasathi.in       | admin123 |

### Optional extras

| What | How |
|---|---|
| **Real photos offline** | `python scripts/download_images.py` saves a Wikipedia photo of every place into `yatrasathi/static/images/places/`. Without it, the browser loads the photos from Wikipedia when online, and shows illustrated placeholders when offline. |
| **LLM answers (OpenAI)** | Copy `.env.example` to `.env` and set `OPENAI_API_KEY=...`. Answers are then written by the LLM using **only** the passages retrieved by RAG. If the key is missing or the call fails, the built-in offline generator is used. |
| **Fresh database** | `python scripts/reset_db.py`, then `python app.py`. |
| **Run tests** | `pytest` (28 tests: NLP, intent model, RAG, recommender, planner, chatbot, pages and API). |

---

## 2. Features (mapped to the project specification)

| Spec item | Where in the app |
|---|---|
| Home page | `/`: hero search, AI assistant card, popular destinations, categories, featured itineraries |
| Explore Karnataka | `/explore`: search (NLP + RAG), category / district / rating filters, sorting, pagination, preview panel, map view |
| Destination details | `/place/<slug>`: overview, history & story (with **Listen**), attractions, nearby places, stay & budget estimate, food, map, reviews, similar places |
| AI Travel Assistant | `/assistant`: multilingual chat with **voice input** and **voice output**, chat history, follow-up suggestions, place cards and itineraries inside replies |
| AI Trip Planner | `/planner`: form (start, destination or *let AI choose*, days, travellers, budget, style, transport, interests) and chat side by side; day-wise timeline, cost breakdown, save trip, PDF download |
| Personalised recommendations | Hybrid recommender (interests, ratings, popularity, distance, season, saved places) |
| Budget-based itinerary generation | Planner estimates transport, stay, food and entry fees, and automatically optimises the style and transport to fit the budget. Example: *“Suggest places in Karnataka for 2 days within ₹5000”* |
| RAG-based tourism information | TF-IDF retrieval over the travel database, the travel guide and admin documents; sources are shown under each answer |
| Multilingual (EN / ಕನ್ನಡ / हिंदी) | Whole UI is translated (language switch in the navbar); the chatbot understands and replies in all three languages |
| Text & voice interaction | Web Speech API speech-to-text (en-IN / kn-IN / hi-IN) and text-to-speech, with a gTTS server fallback for Kannada and Hindi |
| My Account / My Trips | Dashboard, trips (upcoming / saved / completed, dates, status, PDF), profile, interests, language, password, delete account |
| Saved Places | Heart button everywhere; saved places personalise recommendations |
| Travel Guide | About Karnataka, festivals, cuisine, culture, transport, weather, safety, essentials, emergency contacts, FAQs, brochure PDF |
| Nearby Places | `/nearby`: use GPS or pick a city or place; distance-sorted list, category filter, map, directions |
| Admin Dashboard | KPIs, 30-day analytics chart, top destinations, recent itineraries, chat language share, registrations, feedback |
| Destination / user / itinerary / feedback management | `/admin/destinations` (CRUD + image upload), `/admin/users`, `/admin/itineraries`, `/admin/feedback` (with sentiment), `/admin/knowledge` (RAG documents + retrieval tester + rebuild), `/admin/chats`, `/admin/reports` (charts + CSV export) |

---

## 3. System architecture (as in the project report)

```
User Input (text / voice, EN-KN-HI)
   │
   ▼
Input Processing (NLP)          ai/text.py      tokenisation, stop-words, stemming, language detection
   ▼
Query Understanding             ai/nlp.py       destination, start city, days, budget, travellers, interests, style, month
Intent Recognition (ML)         ai/intent.py    TF-IDF (word + char n-grams) + Logistic Regression, plus keyword rules
   ▼
RAG Retrieval System            ai/rag.py       hybrid TF-IDF semantic search + context matching
Travel Database                 models.py       SQLite: destinations, users, trips, chats, feedback, knowledge docs
   ▼
AI Response Generation          ai/chatbot.py   context-aware dialogue (remembers destination, days, budget …)
                                ai/llm.py       optional OpenAI LLM grounded on retrieved passages
Recommendation Engine           ai/recommender.py
Itinerary & Budget Generation   ai/planner.py   clustering, nearest-neighbour route order, cost model, budget optimisation
   ▼
Output Generation               templates + utils/pdf.py (itinerary & brochure PDFs)
Voice Assistant                 static/js/app.js (speech-to-text / text-to-speech) + /api/tts
Final Output Display            responsive web UI, maps (Leaflet), charts (Chart.js)
```

**Data collection → preprocessing** (`yatrasathi/seed.py`): the raw dataset in
`data/destinations/*.json` is cleaned with **pandas** (duplicates removed, missing values filled,
text normalised, ratings, fees and coordinates validated) and stored in SQLite.

---

## 4. Project structure

```
YatraSathi/
├── app.py                    ← run this
├── config.py                 settings (.env supported)
├── requirements.txt
├── run.bat / run.sh          one-click setup + run
├── data/
│   ├── destinations/*.json   62 Karnataka tourist places (EN + ಕನ್ನಡ + हिंदी summaries)
│   ├── knowledge_base.json   travel guide, FAQs, emergency numbers (RAG corpus)
│   ├── intents.json          multilingual intent training data
│   ├── cities.json           starting cities
│   └── featured_itineraries.json
├── yatrasathi/
│   ├── __init__.py           Flask app factory
│   ├── models.py             database models
│   ├── seed.py               preprocessing + demo data
│   ├── i18n.py               UI translations (EN / KN / HI)
│   ├── ai/                   text, nlp, intent, rag, recommender, planner, chatbot, llm, sentiment, engine
│   ├── routes/               main, auth, account, api, admin
│   ├── utils/                pdf, images
│   ├── templates/            HTML pages (user, account, admin)
│   └── static/               css, js, images, vendor libraries (offline)
├── scripts/                  download_images.py, reset_db.py
└── tests/                    pytest suite
```

### Main API endpoints

| Method | URL | Purpose |
|---|---|---|
| POST | `/api/chat` | `{message, session_id?, lang?}` → reply, intent, entities, places, itinerary, sources |
| POST | `/api/itinerary` | `{start, destination or "auto", days, travelers, budget, interests[], style, transport}` |
| GET | `/api/recommendations?interests=Nature,Heritage&budget=5000&days=2` | personalised / budget recommendations |
| GET | `/api/nearby?lat=..&lng=..` | nearest places |
| GET | `/api/destinations[/<slug>]` | destination data |
| POST | `/api/favorites/<slug>` | save / unsave a place |
| POST | `/api/trips/<id>/save` | save a generated itinerary to My Trips |
| POST | `/api/tts` | Kannada / Hindi / English speech (gTTS, needs internet) |
| GET | `/api/health` | engine status |

---

## 5. Try these in the chat

- `Suggest places in Karnataka for 2 days within ₹5000`
- `Suggest a 3 day trip to Coorg from Bangalore` → then `Make it a budget trip` → `Plan for 4 people` → `what to eat there` (context-aware follow-ups)
- `Tell me the story of Hampi` (storytelling mode; press **Listen**)
- `ಹಂಪಿಯ ಕಥೆ ಹೇಳಿ` · `ಬೆಂಗಳೂರಿನಿಂದ ಕೊಡಗಿಗೆ 2 ದಿನದ ಪ್ರವಾಸ`
- `कूर्ग के लिए 3 दिन की यात्रा योजना बनाओ, बजट 10 हजार` · `गोल गुंबज का प्रवेश शुल्क`
- `Best time to visit Jog Falls` · `places near Chikmagalur` · `when is Mysuru Dasara` · `emergency numbers`

---

## 6. Notes and limitations

- Costs, timings and entry fees are **planning estimates**. Confirm current prices before travelling.
- Voice input uses the browser's speech recognition (best in **Chrome / Edge**; needs microphone permission and internet).
  Kannada and Hindi speech output uses the browser voice if one is installed, otherwise gTTS (internet).
- Maps (OpenStreetMap tiles), web fonts and Wikipedia photos need internet. Everything else, including the AI, works offline.
- Without an OpenAI key, Kannada and Hindi answers use the localised summaries and templates. Some long
  descriptions (history, travel guide articles) stay in English. With a key, the LLM answers fully in the chosen language.
- Booking, live weather and live transport data are listed as future enhancements in the project report and are not included.
