"""
Mood Detection NLP Model using TextBlob and Rule-Based Keyword Scoring.
Provides high-fidelity emotion mapping (happy, sad, romantic, excited, relaxed, angry, motivated, fear)
with custom confidence scoring and detailed feedback explanation.
"""

import re
import sys

# Attempt to import TextBlob. Provide local fallback lexicon if missing or error occurs.
try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

# TMDB Genre ID mappings
# Note: "motivated" is mapped to History (36) and Drama (18) to get inspiring true stories and biographical sports dramas.
EMOTION_GENRES = {
    "happy": [35, 16],        # Comedy, Animation
    "sad": [18],              # Drama
    "romantic": [10749],      # Romance
    "excited": [28, 12],      # Action, Adventure
    "relaxed": [99, 10751],   # Documentary, Family
    "angry": [53],            # Thriller
    "motivated": [36, 18],    # History, Drama (inspirational)
    "fear": [27, 9648]        # Horror, Mystery
}

# Emotion Display Metas (emoji and explanation)
EMOTION_META = {
    "happy": {
        "emoji": "😊",
        "explanation": "You're radiating positive vibes! Let's keep the good times rolling with some lighthearted comedies and colorful animations!"
    },
    "sad": {
        "emoji": "😢",
        "explanation": "It's okay to feel down. Let's cozy up with some touching, deep, and comforting dramas that understand your soul."
    },
    "romantic": {
        "emoji": "💖",
        "explanation": "Love is in the air! You are feeling affectionate. Get ready for some heartwarming stories, romantic connections, and deep bonds."
    },
    "excited": {
        "emoji": "🤩",
        "explanation": "Your energy is off the charts! We've lined up some high-octane action and jaw-dropping adventure movies to match your hype!"
    },
    "relaxed": {
        "emoji": "🧘",
        "explanation": "Peace and tranquility. Let's unwind with a soothing family film or an educational, captivating documentary."
    },
    "angry": {
        "emoji": "🔥",
        "explanation": "Feeling a bit heated? Channel that intense energy into a gripping, suspenseful thriller that will keep you on the edge of your seat."
    },
    "motivated": {
        "emoji": "💪",
        "explanation": "You're ready to conquer the world! Here are some powerful historical dramas and stories of ultimate human triumph to inspire you."
    },
    "fear": {
        "emoji": "😱",
        "explanation": "Feeling spooky or anxious? Dive into the dark side with spine-chilling horror movies and puzzle-filled mystery thrillers!"
    }
}

# Keyword mappings for keyword-boosting (lexicon fallback and reinforcement)
EMOTION_KEYWORDS = {
    "happy": ["happy", "glad", "joy", "cheerful", "smile", "delight", "awesome", "fantastic", "great", "good", "wonderful", "celebrate", "laugh"],
    "sad": ["sad", "lonely", "blue", "cry", "depressed", "grief", "sorrow", "unhappy", "down", "gloomy", "heartbroken", "hurt", "miserable"],
    "romantic": ["love", "romance", "romantic", "heart", "sweetheart", "date", "crush", "kiss", "darling", "flirt", "passionate", "beloved"],
    "excited": ["excited", "thrilled", "hyped", "ecstatic", "adventure", "energy", "action", "eager", "pumped", "enthusiastic", "party", "hurrah"],
    "relaxed": ["calm", "relaxed", "peaceful", "chill", "quiet", "serene", "cozy", "sleepy", "rest", "lazy", "smooth", "soothe", "mellow"],
    "angry": ["angry", "mad", "furious", "annoyed", "hate", "rage", "pissed", "frustrated", "irritated", "fuming", "outraged", "dislike"],
    "motivated": ["motivated", "work", "study", "gym", "run", "goal", "achieve", "inspire", "success", "focus", "win", "strive", "determined", "hardwork"],
    "fear": ["fear", "scared", "afraid", "ghost", "horror", "creep", "terrify", "dark", "spooky", "nightmare", "anxious", "panic", "dread"]
}

def detect_emotion(text: str) -> dict:
    """
    Analyzes raw text sentiment and keyword patterns, maps to one of 8 emotions,
    and returns a structured dict with TMDB genre IDs, emoji, explanation, and confidence.
    """
    if not text or not text.strip():
        # Default fallback for empty strings
        return {
            "emotion": "relaxed",
            "emoji": EMOTION_META["relaxed"]["emoji"],
            "explanation": "No worries! Sit back and enjoy these peaceful, relaxing recommendations.",
            "confidence": 0.50,
            "genres": EMOTION_GENRES["relaxed"],
            "polarity": 0.0,
            "subjectivity": 0.0
        }

    cleaned_text = text.lower().strip()
    
    # Calculate polarity and subjectivity using TextBlob if available
    polarity = 0.0
    subjectivity = 0.5  # Neutral default
    
    if HAS_TEXTBLOB:
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
        except Exception as e:
            # Catch possible NLTK download/missing corpora issues gracefully
            print(f"TextBlob warning: {e}. Falling back to keyword-based metrics.", file=sys.stderr)

    # Keyword scoring
    keyword_scores = {emotion: 0 for emotion in EMOTION_KEYWORDS}
    for emotion, words in EMOTION_KEYWORDS.items():
        for word in words:
            # Use regex word boundary matching to avoid substring clashes (e.g. "glad" matching "gladiator")
            matches = len(re.findall(r'\b' + re.escape(word) + r'\b', cleaned_text))
            keyword_scores[emotion] += matches

    # Determine base emotion scores by combining sentiment polarity/subjectivity and keyword boosts
    emotion_weights = {emotion: 0.0 for emotion in EMOTION_KEYWORDS}

    # Happy scoring: high polarity, positive keywords
    emotion_weights["happy"] = keyword_scores["happy"] * 1.5
    if polarity > 0.3:
        emotion_weights["happy"] += (polarity * 2.0)
    elif polarity > 0.0:
        emotion_weights["happy"] += (polarity * 1.0)

    # Sad scoring: negative polarity, sad keywords
    emotion_weights["sad"] = keyword_scores["sad"] * 1.5
    if polarity < -0.2:
        emotion_weights["sad"] += (abs(polarity) * 2.0)
    elif polarity < 0.0:
        emotion_weights["sad"] += (abs(polarity) * 0.8)

    # Romantic scoring: keywords, moderate positive polarity, high subjectivity
    emotion_weights["romantic"] = keyword_scores["romantic"] * 2.0
    if polarity > 0.1:
        emotion_weights["romantic"] += (polarity * 0.8)
    if subjectivity > 0.4:
        emotion_weights["romantic"] += (subjectivity * 0.6)

    # Excited scoring: high polarity, high subjectivity, exclamation marks, keywords
    emotion_weights["excited"] = keyword_scores["excited"] * 2.0
    if polarity > 0.4:
        emotion_weights["excited"] += (polarity * 1.5)
    if subjectivity > 0.5:
        emotion_weights["excited"] += (subjectivity * 1.0)
    if "!" in text:
        emotion_weights["excited"] += 0.5

    # Relaxed scoring: neutral polarity, low subjectivity, keywords
    emotion_weights["relaxed"] = keyword_scores["relaxed"] * 1.8
    if -0.1 <= polarity <= 0.3:
        emotion_weights["relaxed"] += 0.8
    if subjectivity < 0.4:
        emotion_weights["relaxed"] += (0.6 - subjectivity)

    # Angry scoring: high negative polarity, high subjectivity, keywords, ALL CAPS boost
    emotion_weights["angry"] = keyword_scores["angry"] * 2.0
    if polarity < -0.3:
        emotion_weights["angry"] += (abs(polarity) * 1.5)
    if subjectivity > 0.4:
        emotion_weights["angry"] += (subjectivity * 0.8)
    if text.isupper() and len(text) > 4:
        emotion_weights["angry"] += 1.0

    # Motivated scoring: positive polarity, moderate subjectivity, keywords
    emotion_weights["motivated"] = keyword_scores["motivated"] * 2.0
    if polarity > 0.1:
        emotion_weights["motivated"] += (polarity * 1.0)
    if 0.2 <= subjectivity <= 0.7:
        emotion_weights["motivated"] += 0.5

    # Fear scoring: negative polarity, high subjectivity, keywords
    emotion_weights["fear"] = keyword_scores["fear"] * 2.0
    if polarity < 0.0:
        emotion_weights["fear"] += (abs(polarity) * 1.0)
    if subjectivity > 0.4:
        emotion_weights["fear"] += (subjectivity * 1.0)

    # Select the emotion with the highest score
    detected = max(emotion_weights, key=emotion_weights.get)
    max_score = emotion_weights[detected]

    # Calculate confidence percentage (min 45%, capped at 98%)
    confidence = 0.50
    if max_score > 0:
        total_score = sum(emotion_weights.values())
        confidence = 0.45 + (max_score / (total_score + 0.1)) * 0.50
    
    # Cap confidence between 0.45 and 0.98
    confidence = min(0.98, max(0.45, confidence))

    # Retrieve metadata for the chosen emotion
    meta = EMOTION_META[detected]

    return {
        "emotion": detected,
        "emoji": meta["emoji"],
        "explanation": meta["explanation"],
        "confidence": round(confidence, 2),
        "genres": EMOTION_GENRES[detected],
        "polarity": round(polarity, 2),
        "subjectivity": round(subjectivity, 2)
    }

if __name__ == "__main__":
    # Small test cases to confirm logic
    test_phrases = [
        "I am so happy and glad today, everything is awesome!",
        "I feel so lonely and sad, just crying in my room.",
        "I love you so much, you are my sweetheart",
        "Let's go on an amazing adventure, I am so hyped!",
        "Just want to sit back, drink tea, and relax in a quiet spot.",
        "I hate this! This is so frustrating and I am extremely angry!",
        "I need to work hard, focus on my goals, and achieve success!",
        "I'm scared of the dark and feel terrified of ghosts."
    ]
    
    print("Testing mood_model NLP mapping:")
    for phrase in test_phrases:
        res = detect_emotion(phrase)
        print(f"Input: '{phrase}'")
        print(f" -> Emotion: {res['emoji']} {res['emotion']} (Conf: {res['confidence']})")
        print(f" -> Explanation: {res['explanation']}\n")
