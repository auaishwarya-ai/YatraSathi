"""Multilingual response templates (English, Kannada, Hindi) for the offline generator."""

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "kn": ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್", "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"],
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
}

CATEGORIES = {
    "kn": {"Heritage": "ಪರಂಪರೆ", "Temples": "ದೇವಾಲಯಗಳು", "Hill Stations": "ಗಿರಿಧಾಮಗಳು", "Waterfalls": "ಜಲಪಾತಗಳು",
           "Beaches": "ಕಡಲತೀರಗಳು", "Wildlife": "ವನ್ಯಜೀವಿ", "Adventure": "ಸಾಹಸ", "Gardens & Parks": "ಉದ್ಯಾನಗಳು"},
    "hi": {"Heritage": "विरासत", "Temples": "मंदिर", "Hill Stations": "हिल स्टेशन", "Waterfalls": "झरने",
           "Beaches": "समुद्र तट", "Wildlife": "वन्यजीव", "Adventure": "साहसिक", "Gardens & Parks": "उद्यान"},
}

T = {
    "en": {
        "greeting": "Namaste! 🙏 I'm YatraSathi, your AI travel assistant for Karnataka. Ask me about places, history, food, best time to visit, or say something like **\"Plan a 3 day trip to Coorg from Bangalore within ₹15,000\"**.",
        "help": "I can help you with:\n- **Trip planning** - day-wise itineraries with cost estimates\n- **Budget-based suggestions** - e.g. *places for 2 days within ₹5000*\n- **Place information** - history, attractions, timings, entry fees\n- **Food, festivals, weather, transport and safety tips**\n\nYou can type or speak in English, ಕನ್ನಡ or हिंदी.",
        "thanks": "You're welcome! 😊 Anything else you'd like to plan?",
        "goodbye": "Happy travels! 🌿 Come back anytime to plan your next Karnataka trip.",
        "ask_place": "Which place would you like to know about? For example: Hampi, Coorg, Mysore Palace or Jog Falls.",
        "fallback": "I'm not sure about that yet. I can help with Karnataka destinations, trip plans, budgets, food, festivals and travel tips. Try asking *\"Tell me about Hampi\"* or *\"Suggest places for 2 days within ₹5000\"*.",
        "best_time": "The best time to visit **{name}** is **{months}**.",
        "monsoon_note": "Waterfalls are at their fullest during the monsoon (July - September), but paths can be slippery.",
        "best_label": "Best time", "day": "Day", "timings": "Timings", "entry": "Entry fee", "free": "Free", "indians": "Indians", "foreigners": "foreigners",
        "ideal": "Ideal duration", "days": "day(s)", "rating": "Rating", "district": "District",
        "tip": "Tip", "how_reach": "How to reach **{name}**", "distance": "About **{km} km** from {city} (≈ {hours} by road).",
        "attractions": "Top attractions in **{name}**:", "food": "Must-try food in and around **{name}**:",
        "nearby": "Places near **{name}**:", "story_title": "📖 **The story of {name}**",
        "story_outro": "Would you like me to plan a trip to {name}?",
        "recommend_intro": "Here are my top picks{criteria}:", "for_interest": " for {interests}",
        "within_budget": " that fit **₹{budget}** for {days} day(s), {travelers} traveller(s) from {city}",
        "est_cost": "est. ₹{cost}", "nothing_fits": "No destination fits **₹{budget}** for {days} day(s) and {travelers} traveller(s) from {city}. The most affordable options are:",
        "plan_intro": "Here's a perfect **{days}-day trip to {name}** from {city} for {travelers} traveller(s)! ✨",
        "plan_total": "**Estimated total: ₹{total}** (₹{pp} per person) · {style} stay · travel by {transport}",
        "budget_ok": "✅ Fits your budget of ₹{budget} (₹{remaining} to spare).",
        "budget_optimized": "💡 Optimised to fit your ₹{budget} budget: {changes}.",
        "budget_over": "⚠️ This trip needs about ₹{total}, above your ₹{budget} budget.",
        "suggest_days": " A {days}-day version fits your budget.",
        "cost_breakdown": "Cost breakdown", "transport": "Transport", "stay": "Stay", "food_cost": "Food", "entry_fees": "Entry fees",
        "local": "Local travel", "misc": "Misc (5%)",
        "budget_intro": "Estimated cost for **{days} day(s) in {name}** for {travelers} traveller(s) from {city}:",
        "estimate_note": "Costs are estimates - please confirm current prices before travelling.",
        "changes": {"style": "{a} → {b} stay", "transport": "{a} → {b}", "dropped_paid": "skipped optional paid activities"},
        "styles": {"budget": "budget", "standard": "standard", "luxury": "luxury"},
        "transports": {"bus": "bus", "car": "cab", "train": "train"},
        "emergency": "Emergency numbers: **112** (all emergencies), Police **100**, Ambulance **108**, Tourist helpline **1363**, Women helpline **1091**.",
        "from_guide": "From the YatraSathi travel guide:",
        "suggestions": {
            "default": ["Plan a 3 day trip to Coorg", "Suggest places for 2 days within ₹5000", "Tell me the story of Hampi", "Best time to visit Jog Falls"],
            "place": ["Best time to visit {name}", "Must try food in {name}", "How to reach {name}", "Plan a 2 day trip to {name}"],
            "plan": ["Make it a budget trip", "Plan for 4 people", "Best time to visit {name}", "Tell me the story of {name}"],
        },
    },
    "kn": {
        "greeting": "ನಮಸ್ಕಾರ! 🙏 ನಾನು ಯಾತ್ರಾಸಾಥಿ, ಕರ್ನಾಟಕದ ನಿಮ್ಮ ಎಐ ಪ್ರವಾಸ ಸಹಾಯಕ. ಸ್ಥಳಗಳು, ಇತಿಹಾಸ, ಆಹಾರ, ಭೇಟಿ ನೀಡಲು ಉತ್ತಮ ಸಮಯದ ಬಗ್ಗೆ ಕೇಳಿ ಅಥವಾ **\"ಬೆಂಗಳೂರಿನಿಂದ ಕೊಡಗಿಗೆ 3 ದಿನದ ಪ್ರವಾಸ ಯೋಜನೆ\"** ಎಂದು ಹೇಳಿ.",
        "help": "ನಾನು ಇವುಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ:\n- **ಪ್ರವಾಸ ಯೋಜನೆ** - ದಿನವಾರು ವೇಳಾಪಟ್ಟಿ ಮತ್ತು ವೆಚ್ಚ\n- **ಬಜೆಟ್ ಆಧಾರಿತ ಸಲಹೆಗಳು**\n- **ಸ್ಥಳದ ಮಾಹಿತಿ** - ಇತಿಹಾಸ, ಆಕರ್ಷಣೆಗಳು, ಸಮಯ, ಶುಲ್ಕ\n- **ಆಹಾರ, ಹಬ್ಬಗಳು, ಹವಾಮಾನ ಮತ್ತು ಸುರಕ್ಷತೆ**\n\nಇಂಗ್ಲಿಷ್, ಕನ್ನಡ ಅಥವಾ ಹಿಂದಿಯಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಮಾತನಾಡಿ.",
        "thanks": "ಸ್ವಾಗತ! 😊 ಇನ್ನೇನಾದರೂ ಯೋಜಿಸಬೇಕೇ?",
        "goodbye": "ಶುಭ ಪ್ರಯಾಣ! 🌿 ಮುಂದಿನ ಪ್ರವಾಸಕ್ಕೆ ಮತ್ತೆ ಬನ್ನಿ.",
        "ask_place": "ಯಾವ ಸ್ಥಳದ ಬಗ್ಗೆ ತಿಳಿಯಬೇಕು? ಉದಾ: ಹಂಪಿ, ಕೊಡಗು, ಮೈಸೂರು ಅರಮನೆ ಅಥವಾ ಜೋಗ ಜಲಪಾತ.",
        "fallback": "ಕ್ಷಮಿಸಿ, ಅದರ ಬಗ್ಗೆ ಖಚಿತ ಮಾಹಿತಿ ಇಲ್ಲ. ಕರ್ನಾಟಕದ ತಾಣಗಳು, ಪ್ರವಾಸ ಯೋಜನೆ, ಬಜೆಟ್, ಆಹಾರ ಮತ್ತು ಹಬ್ಬಗಳ ಬಗ್ಗೆ ಕೇಳಿ. ಉದಾ: *\"ಹಂಪಿಯ ಬಗ್ಗೆ ತಿಳಿಸಿ\"*.",
        "best_time": "**{name}** ಭೇಟಿ ನೀಡಲು ಉತ್ತಮ ಸಮಯ **{months}**.",
        "monsoon_note": "ಮಳೆಗಾಲದಲ್ಲಿ (ಜುಲೈ - ಸೆಪ್ಟೆಂಬರ್) ಜಲಪಾತಗಳು ತುಂಬಿ ಹರಿಯುತ್ತವೆ, ಆದರೆ ದಾರಿ ಜಾರುತ್ತದೆ.",
        "best_label": "ಉತ್ತಮ ಸಮಯ", "day": "ದಿನ", "timings": "ಸಮಯ", "entry": "ಪ್ರವೇಶ ಶುಲ್ಕ", "free": "ಉಚಿತ", "indians": "ಭಾರತೀಯರಿಗೆ", "foreigners": "ವಿದೇಶಿಯರಿಗೆ",
        "ideal": "ಸೂಕ್ತ ಅವಧಿ", "days": "ದಿನ", "rating": "ರೇಟಿಂಗ್", "district": "ಜಿಲ್ಲೆ",
        "tip": "ಸಲಹೆ", "how_reach": "**{name}** ತಲುಪುವುದು ಹೇಗೆ", "distance": "{city} - {name} ನಡುವೆ ಸುಮಾರು **{km} ಕಿ.ಮೀ** (ರಸ್ತೆ ಮೂಲಕ ≈ {hours}).",
        "attractions": "**{name}** ಪ್ರಮುಖ ಆಕರ್ಷಣೆಗಳು:", "food": "**{name}** ಸುತ್ತಮುತ್ತ ಸವಿಯಬೇಕಾದ ಆಹಾರ:",
        "nearby": "**{name}** ಸಮೀಪದ ಸ್ಥಳಗಳು:", "story_title": "📖 **{name} ಕಥೆ**",
        "story_outro": "{name} ಪ್ರವಾಸದ ಯೋಜನೆ ಮಾಡಬೇಕೇ?",
        "recommend_intro": "ನನ್ನ ಶಿಫಾರಸುಗಳು{criteria}:", "for_interest": " ({interests})",
        "within_budget": " - {days} ದಿನ, {travelers} ಜನ, **₹{budget}** ಬಜೆಟ್ (ಆರಂಭ: {city})",
        "est_cost": "ಅಂದಾಜು ₹{cost}", "nothing_fits": "**₹{budget}** ಬಜೆಟ್‌ನಲ್ಲಿ {days} ದಿನ, {travelers} ಜನರಿಗೆ (ಆರಂಭ: {city}) ಯಾವ ತಾಣವೂ ಸಿಗಲಿಲ್ಲ. ಕಡಿಮೆ ವೆಚ್ಚದ ಆಯ್ಕೆಗಳು:",
        "plan_intro": "**{name} - {days} ದಿನದ ಪ್ರವಾಸ** ಯೋಜನೆ ಸಿದ್ಧ! ✨ (ಆರಂಭ: {city}, {travelers} ಜನ)",
        "plan_total": "**ಒಟ್ಟು ಅಂದಾಜು ವೆಚ್ಚ: ₹{total}** (ಪ್ರತಿ ವ್ಯಕ್ತಿಗೆ ₹{pp}) · {style} ವಸತಿ · {transport} ಪ್ರಯಾಣ",
        "budget_ok": "✅ ನಿಮ್ಮ ₹{budget} ಬಜೆಟ್‌ನೊಳಗಿದೆ (₹{remaining} ಉಳಿತಾಯ).",
        "budget_optimized": "💡 ನಿಮ್ಮ ₹{budget} ಬಜೆಟ್‌ಗೆ ಹೊಂದುವಂತೆ ಬದಲಿಸಲಾಗಿದೆ: {changes}.",
        "budget_over": "⚠️ ಈ ಪ್ರವಾಸಕ್ಕೆ ಸುಮಾರು ₹{total} ಬೇಕು, ಇದು ನಿಮ್ಮ ₹{budget} ಬಜೆಟ್‌ಗಿಂತ ಹೆಚ್ಚು.",
        "suggest_days": " {days} ದಿನದ ಪ್ರವಾಸ ನಿಮ್ಮ ಬಜೆಟ್‌ಗೆ ಹೊಂದುತ್ತದೆ.",
        "cost_breakdown": "ವೆಚ್ಚದ ವಿವರ", "transport": "ಪ್ರಯಾಣ", "stay": "ವಸತಿ", "food_cost": "ಆಹಾರ", "entry_fees": "ಪ್ರವೇಶ ಶುಲ್ಕ",
        "local": "ಸ್ಥಳೀಯ ಪ್ರಯಾಣ", "misc": "ಇತರೆ (5%)",
        "budget_intro": "**{name} - {days} ದಿನ** ಅಂದಾಜು ವೆಚ್ಚ (ಆರಂಭ: {city}, {travelers} ಜನ):",
        "estimate_note": "ವೆಚ್ಚಗಳು ಅಂದಾಜು ಮಾತ್ರ - ಪ್ರಯಾಣಕ್ಕೂ ಮುನ್ನ ದರಗಳನ್ನು ಖಚಿತಪಡಿಸಿ.",
        "changes": {"style": "{a} → {b} ವಸತಿ", "transport": "{a} → {b}", "dropped_paid": "ಐಚ್ಛಿಕ ಶುಲ್ಕದ ಚಟುವಟಿಕೆಗಳನ್ನು ಬಿಡಲಾಗಿದೆ"},
        "styles": {"budget": "ಕಡಿಮೆ ವೆಚ್ಚದ", "standard": "ಸಾಮಾನ್ಯ", "luxury": "ಐಷಾರಾಮಿ"},
        "transports": {"bus": "ಬಸ್", "car": "ಕ್ಯಾಬ್", "train": "ರೈಲು"},
        "emergency": "ತುರ್ತು ಸಂಖ್ಯೆಗಳು: **112** (ಎಲ್ಲಾ ತುರ್ತು), ಪೊಲೀಸ್ **100**, ಆಂಬ್ಯುಲೆನ್ಸ್ **108**, ಪ್ರವಾಸಿ ಸಹಾಯವಾಣಿ **1363**, ಮಹಿಳಾ ಸಹಾಯವಾಣಿ **1091**.",
        "from_guide": "ಯಾತ್ರಾಸಾಥಿ ಪ್ರವಾಸ ಮಾರ್ಗದರ್ಶಿಯಿಂದ:",
        "suggestions": {
            "default": ["ಕೊಡಗಿಗೆ 3 ದಿನದ ಪ್ರವಾಸ ಯೋಜನೆ", "5000 ರೂಪಾಯಿಯಲ್ಲಿ 2 ದಿನದ ಸ್ಥಳಗಳು", "ಹಂಪಿಯ ಕಥೆ ಹೇಳಿ", "ಜೋಗ ಜಲಪಾತಕ್ಕೆ ಉತ್ತಮ ಸಮಯ"],
            "place": ["{name} ಭೇಟಿಗೆ ಉತ್ತಮ ಸಮಯ", "{name} ಪ್ರಸಿದ್ಧ ಆಹಾರ", "{name} ತಲುಪುವುದು ಹೇಗೆ", "{name} 2 ದಿನದ ಪ್ರವಾಸ ಯೋಜನೆ"],
            "plan": ["ಕಡಿಮೆ ಬಜೆಟ್ ಪ್ರವಾಸ", "4 ಜನರಿಗೆ ಯೋಜನೆ", "{name} ಭೇಟಿಗೆ ಉತ್ತಮ ಸಮಯ", "{name} ಕಥೆ ಹೇಳಿ"],
        },
    },
    "hi": {
        "greeting": "नमस्ते! 🙏 मैं यात्रासाथी हूँ, कर्नाटक के लिए आपका एआई यात्रा सहायक। जगहों, इतिहास, खाने या घूमने के सही समय के बारे में पूछें, या कहें **\"बेंगलुरु से कूर्ग की 3 दिन की यात्रा योजना बनाओ\"**।",
        "help": "मैं इनमें मदद कर सकता हूँ:\n- **यात्रा योजना** - दिन-वार कार्यक्रम और खर्च\n- **बजट के अनुसार सुझाव**\n- **जगह की जानकारी** - इतिहास, आकर्षण, समय, शुल्क\n- **खाना, त्योहार, मौसम और सुरक्षा सुझाव**\n\nअंग्रेज़ी, कन्नड़ या हिंदी में लिखें या बोलें।",
        "thanks": "आपका स्वागत है! 😊 और कुछ प्लान करना है?",
        "goodbye": "शुभ यात्रा! 🌿 अगली कर्नाटक यात्रा के लिए फिर आइए।",
        "ask_place": "आप किस जगह के बारे में जानना चाहते हैं? जैसे: हम्पी, कूर्ग, मैसूर पैलेस या जोग फॉल्स।",
        "fallback": "माफ़ कीजिए, इसकी पक्की जानकारी मेरे पास नहीं है। कर्नाटक के पर्यटन स्थल, यात्रा योजना, बजट, खाना और त्योहारों के बारे में पूछें। जैसे: *\"हम्पी के बारे में बताओ\"*।",
        "best_time": "**{name}** घूमने का सबसे अच्छा समय **{months}** है।",
        "monsoon_note": "मानसून (जुलाई - सितंबर) में झरने पूरे उफ़ान पर होते हैं, लेकिन रास्ते फिसलन भरे होते हैं।",
        "best_label": "सबसे अच्छा समय", "day": "दिन", "timings": "समय", "entry": "प्रवेश शुल्क", "free": "निःशुल्क", "indians": "भारतीयों के लिए", "foreigners": "विदेशियों के लिए",
        "ideal": "उपयुक्त अवधि", "days": "दिन", "rating": "रेटिंग", "district": "ज़िला",
        "tip": "सुझाव", "how_reach": "**{name}** कैसे पहुँचें", "distance": "{city} से लगभग **{km} किमी** (सड़क से ≈ {hours})।",
        "attractions": "**{name}** के प्रमुख आकर्षण:", "food": "**{name}** और आसपास ज़रूर चखें:",
        "nearby": "**{name}** के पास की जगहें:", "story_title": "📖 **{name} की कहानी**",
        "story_outro": "क्या मैं {name} की यात्रा योजना बनाऊँ?",
        "recommend_intro": "मेरे सुझाव{criteria}:", "for_interest": " ({interests})",
        "within_budget": " - {city} से {days} दिन, {travelers} लोगों के लिए **₹{budget}** में",
        "est_cost": "अनुमानित ₹{cost}", "nothing_fits": "{city} से {days} दिन और {travelers} लोगों के लिए **₹{budget}** में कोई जगह फिट नहीं हुई। सबसे किफ़ायती विकल्प:",
        "plan_intro": "{city} से {travelers} लोगों के लिए **{name} की {days} दिन की यात्रा** तैयार है! ✨",
        "plan_total": "**कुल अनुमानित खर्च: ₹{total}** (प्रति व्यक्ति ₹{pp}) · {style} ठहराव · {transport} से यात्रा",
        "budget_ok": "✅ आपके ₹{budget} बजट में (₹{remaining} बचत)।",
        "budget_optimized": "💡 आपके ₹{budget} बजट के अनुसार बदला गया: {changes}।",
        "budget_over": "⚠️ इस यात्रा में लगभग ₹{total} लगेंगे, जो आपके ₹{budget} बजट से अधिक है।",
        "suggest_days": " {days} दिन की यात्रा आपके बजट में आ जाएगी।",
        "cost_breakdown": "खर्च का विवरण", "transport": "यात्रा", "stay": "ठहराव", "food_cost": "भोजन", "entry_fees": "प्रवेश शुल्क",
        "local": "स्थानीय यात्रा", "misc": "अन्य (5%)",
        "budget_intro": "{city} से {travelers} लोगों के लिए **{name} में {days} दिन** का अनुमानित खर्च:",
        "estimate_note": "खर्च अनुमानित है - यात्रा से पहले मौजूदा दरें जाँच लें।",
        "changes": {"style": "{a} → {b} ठहराव", "transport": "{a} → {b}", "dropped_paid": "वैकल्पिक सशुल्क गतिविधियाँ हटाई गईं"},
        "styles": {"budget": "किफ़ायती", "standard": "सामान्य", "luxury": "लक्ज़री"},
        "transports": {"bus": "बस", "car": "कैब", "train": "ट्रेन"},
        "emergency": "आपातकालीन नंबर: **112** (सभी आपात स्थितियाँ), पुलिस **100**, एम्बुलेंस **108**, पर्यटक हेल्पलाइन **1363**, महिला हेल्पलाइन **1091**।",
        "from_guide": "यात्रासाथी ट्रैवल गाइड से:",
        "suggestions": {
            "default": ["कूर्ग की 3 दिन की यात्रा योजना", "5000 रुपये में 2 दिन कहाँ जाएँ", "हम्पी की कहानी सुनाओ", "जोग फॉल्स कब जाएँ"],
            "place": ["{name} जाने का सबसे अच्छा समय", "{name} का प्रसिद्ध खाना", "{name} कैसे पहुँचें", "{name} की 2 दिन की यात्रा योजना"],
            "plan": ["बजट यात्रा बनाओ", "4 लोगों के लिए योजना", "{name} जाने का सबसे अच्छा समय", "{name} की कहानी सुनाओ"],
        },
    },
}


def t(lang, key):
    return T.get(lang, T["en"]).get(key, T["en"].get(key, key))


def month_range(lang, start, end):
    names = MONTHS.get(lang, MONTHS["en"])
    if start == 1 and end == 12:
        return {"en": "all year round", "kn": "ವರ್ಷವಿಡೀ", "hi": "साल भर"}.get(lang, "all year round")
    return f"{names[start - 1]} - {names[end - 1]}"


def money(value):
    """Indian digit grouping: 1234567 -> 12,34,567"""
    value = int(round(value or 0))
    s = str(abs(value))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return ("-" if value < 0 else "") + s


def category_name(lang, category):
    return CATEGORIES.get(lang, {}).get(category, category)
