import os
import re
from typing import List, Tuple, Optional

from bson import ObjectId
from sentence_transformers import SentenceTransformer, util
from google import genai
from google.genai import types


# In-memory index built at startup from backend/knowledge_base.txt
_embed_model: Optional[SentenceTransformer] = None
_kb_chunks: List[str] = []
_kb_embeddings = None
_gemini_client = None

# Configuration for confidence thresholds
MIN_CONFIDENCE_THRESHOLD = 0.25  # Lowered from 0.35 - be more permissive
MIN_COMPOSITE_THRESHOLD = 0.30   # Lowered from 0.40 - be more permissive

# Legal keywords for intent detection
LEGAL_KEYWORDS = {
    "court", "judge", "lawyer", "advocate", "case", "fir", "police", "complaint", 
    "legal", "law", "act", "section", "dispute", "property", "land", "aadhaar", 
    "aadhar", "licence", "license", "consumer", "cyber", "crime", "fraud", 
    "mediation", "family", "divorce", "custody", "maintenance", "inheritance",
    "tenant", "landlord", "bail", "arrest", "rights", "constitution", "appeal",
    "petition", "writ", "supreme", "high", "district", "magistrate", "sessions",
    "civil", "criminal", "evidence", "witness", "summons", "notice", "hearing",
    "judgment", "order", "execution", "attachment", "injunction", "damages",
    "compensation", "fine", "penalty", "punishment", "sentence", "probation",
    "parole", "legal aid", "nalsa", "lok adalat", "arbitration", "conciliation",
    "registration", "stamp duty", "mutation", "title deed", "sale deed",
    "power of attorney", "will", "succession", "probate", "guardian", "minor",
    "adoption", "dowry", "domestic violence", "harassment", "stalking", "rape",
    "molestation", "cheating", "forgery", "theft", "robbery", "burglary",
    "embezzlement", "bribery", "corruption", "defamation", "slander", "libel",
    "contract", "agreement", "breach", "performance", "specific performance",
    "quantum meruit", "quasi contract", "tort", "negligence", "nuisance",
    "trespass", "conversion", "bailment", "pledge", "mortgage", "lien",
    "partnership", "company", "corporate", "director", "shareholder", "winding up",
    "insolvency", "bankruptcy", "debt", "recovery", "execution", "attachment",
    "garnishee", "receivership", "liquidation", "reconstruction", "merger",
    "acquisition", "takeover", "competition", "monopoly", "cartel", "dumping",
    "patent", "copyright", "trademark", "design", "geographical indication",
    "trade secret", "passing off", "infringement", "piracy", "counterfeit",
    "environment", "pollution", "forest", "wildlife", "mining", "water",
    "air", "noise", "waste", "hazardous", "nuclear", "radiation", "safety",
    "labour", "employment", "wages", "bonus", "gratuity", "provident fund",
    "employee", "employer", "industrial", "trade union", "strike", "lockout",
    "retrenchment", "lay off", "closure", "compensation", "workmen", "factories",
    "shops", "establishments", "contract labour", "migrant", "child labour",
    "women", "maternity", "sexual harassment", "equal pay", "disability",
    "reservation", "quota", "scheduled caste", "scheduled tribe", "other backward class",
    "minority", "religion", "caste", "untouchability", "atrocity", "protection",
    "human rights", "fundamental rights", "directive principles", "emergency",
    "president", "prime minister", "parliament", "legislature", "executive",
    "judiciary", "federal", "state", "local", "panchayat", "municipality",
    "corporation", "district collector", "tehsildar", "patwari", "village",
    "block", "subdivision", "circle", "range", "beat", "police station",
    "thana", "outpost", "chowki", "beat", "patrolling", "investigation",
    "charge sheet", "challan", "cognizable", "non-cognizable", "bailable",
    "non-bailable", "warrant", "summons", "proclamation", "attachment", "search",
    "seizure", "recovery", "identification", "test identification", "narco",
    "polygraph", "brain mapping", "encounter", "custodial", "remand", "transit",
    "production", "surrender", "anticipatory", "regular", "interim", "ad-interim",
    "stay", "vacation", "modification", "review", "revision", "appeal", "writ",
    "habeas corpus", "mandamus", "prohibition", "certiorari", "quo-warranto",
    "consumer protection", "edaakhil", "district consumer", "state consumer",
    "national consumer", "redressal commission", "defective goods", "deficient services",
    "unfair trade practices", "misleading advertisement", "product liability",
    "service charges", "banking", "insurance", "telecom", "electricity", "gas",
    "water", "transport", "railways", "airways", "roadways", "shipping", "postal",
    "courier", "delivery", "e-commerce", "online", "digital", "internet", "website",
    "mobile app", "software", "hardware", "data", "privacy", "personal information",
    "consent", "processing", "storage", "transfer", "breach", "notification",
    "grievance", "officer", "authority", "board", "commission", "tribunal",
    "appellate", "revisional", "supervisory", "administrative", "quasi-judicial",
    "url", "website", "link", "portal", "online", "report", "file", "register"
}


def _is_legal_query(query: str) -> bool:
    """Check if the query contains legal-related keywords."""
    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    
    # Check for direct legal keyword matches
    if query_words & LEGAL_KEYWORDS:
        return True
    
    # Check for common legal phrases
    legal_phrases = [
        "how to file", "where to file", "where to report", "how to report",
        "guide me", "please guide", "process of filing", "filing process",
        "step by step", "what is the procedure", "how do i", "what should i do",
        "legal aid", "consumer complaint", "police complaint", "cyber crime", 
        "land dispute", "family dispute", "lost document", "duplicate", 
        "aadhaar", "aadhar", "licence", "license", "court case", "legal advice", 
        "lawyer", "advocate", "fir", "complaint", "tell me the url", "give me link",
        "website", "portal", "online registration", "how to apply", "filing the case",
        "file a case", "court procedure", "what documents", "which court",
        "legal process", "procedure", "next steps", "what to do next"
    ]
    
    for phrase in legal_phrases:
        if phrase in query_lower:
            return True
    
    # Additional check: if query contains process/procedure words + any legal keyword
    process_words = ["process", "procedure", "guide", "steps", "how", "what", "filing", "file"]
    if any(word in query_lower for word in process_words) and query_words & LEGAL_KEYWORDS:
        return True
    
    return False


def _read_knowledge_base(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
            lines = txt.splitlines()
            cleaned_lines = [l for l in lines if not l.strip().lower().startswith('department of justice')]
            return "\n".join(cleaned_lines)
    except FileNotFoundError:
        return ""


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Simple sliding-window text chunker."""
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    for p in paragraphs:
        if len(p) <= chunk_size:
            chunks.append(p)
        else:
            start = 0
            while start < len(p):
                end = min(start + chunk_size, len(p))
                chunks.append(p[start:end])
                if end == len(p):
                    break
                start = end - overlap if end - overlap > start else end
    return chunks


def _clean_chunk_text(s: str) -> str:
    """Sanitize a chunk for display: remove markdown headers and noisy lines."""
    if not s:
        return s
    lines = [l.strip() for l in s.splitlines() if l.strip()]
    cleaned = []
    for l in lines:
        if l.startswith("#"):
            header = l.lstrip('#').strip()
            if header:
                cleaned.append(header)
            continue
        if l.lower().startswith('title:'):
            cleaned.append(l.split(':', 1)[1].strip())
            continue
        cleaned.append(l)
    out = " ".join(cleaned)
    return " ".join(out.split())


async def load_nlp_resources() -> None:
    """Load embedding model, Gemini client and build an in-memory vector index from knowledge_base.txt."""
    global _embed_model, _kb_chunks, _kb_embeddings, _gemini_client
    
    print("Loading embedding model...")
    # Sentence-BERT model for semantic similarity
    _embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print("Initializing Gemini client...")
    # Initialize Gemini client - API key should be in GEMINI_API_KEY environment variable
    try:
        _gemini_client = genai.Client()
        print("Gemini client initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize Gemini client: {e}")
        print("Make sure GEMINI_API_KEY environment variable is set")
        _gemini_client = None

    print("Building knowledge base index...")
    # Build KB index from file
    kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_base.txt")
    kb_text = _read_knowledge_base(kb_path)
    if not kb_text:
        _kb_chunks = []
        _kb_embeddings = None
        return

    _kb_chunks = _chunk_text(kb_text, chunk_size=1000, overlap=200)
    if _kb_chunks:
        _kb_embeddings = _embed_model.encode(_kb_chunks, convert_to_tensor=True, normalize_embeddings=True)
    
    print("NLP resources loaded successfully!")


async def _vector_search(query: str, top_k: int = 3) -> List[Tuple[str, float]]:
    """Return top_k matching KB chunks and their similarity scores."""
    global _embed_model, _kb_chunks, _kb_embeddings
    if not _kb_chunks or _embed_model is None or _kb_embeddings is None:
        return []
    query_emb = _embed_model.encode(query, convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(query_emb, _kb_embeddings)[0]
    vals, idxs = scores.topk(min(top_k, len(_kb_chunks)))
    results: List[Tuple[str, float]] = []
    for v, i in zip(vals, idxs):
        results.append((_kb_chunks[int(i)], float(v)))
    return results


async def run_gemini_generation(user_query: str, context: str, conversation_history: List[Tuple[str, str]] = None) -> str:
    """Generate response using Gemini API with proper prompting and conversation history."""
    global _gemini_client
    
    if _gemini_client is None:
        return ""
    
    if conversation_history is None:
        conversation_history = []
    
    try:
        # Build conversation history for multi-turn chat
        contents = []
        
        # Add system context
        if context:
            context_section = f"""Context from Knowledge Base:
{context}

Important: If the user is asking about "process", "procedure", "how to file", "guide me", or similar procedural questions, provide detailed step-by-step instructions from the context. Don't give generic responses - give specific, actionable steps they can follow."""
        else:
            context_section = """Note: You have access to the conversation history below. Please use that context to answer the user's question accurately."""
        
        system_context = f"""You are an official Department of Justice (India) chatbot assistant. Your role is to help Indian citizens with legal queries, court procedures, and government services.

Based on the provided context, answer the user's question in a helpful, accurate, and citizen-friendly manner. Follow these guidelines:

1. Be comprehensive and detailed when user asks for "process", "procedure", "steps", or "guide me"
2. Always include relevant URLs/links when available in the context
3. Use simple, clear language that common citizens can understand
4. Focus on practical, actionable information with step-by-step guidance
5. If the context mentions specific procedures, explain them completely with all steps
6. For government services, mention both online and offline options when available
7. Use bullet points or numbered lists for step-by-step processes
8. Include required documents, fees, and timelines when mentioned in context
9. If user is asking follow-up questions about legal processes, assume they want detailed procedural guidance

{context_section}"""

        # If no history, add system context with first user query
        if not conversation_history:
            contents.append({
                "role": "user",
                "parts": [{"text": f"{system_context}\n\nUser Question: {user_query}"}]
            })
        else:
            # Add conversation history (alternating user and model messages)
            for role, text in conversation_history:
                contents.append({
                    "role": role,
                    "parts": [{"text": text}]
                })
            
            # For multi-turn conversations, add current query with context
            contents.append({
                "role": "user",
                "parts": [{"text": f"{system_context}\n\nUser Question: {user_query}"}]
            })

        # Generate response with thinking disabled for faster response
        response = _gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),  # Disable thinking for speed
                temperature=0.7,
                max_output_tokens=300,  # Keep responses concise
                top_p=0.9
            )
        )
        
        if response and response.text:
            answer = response.text.strip()
            # Basic validation - ensure it's a meaningful response
            if len(answer.split()) >= 5 and not answer.lower().startswith("i don't"):
                return answer
        
        return ""
        
    except Exception as e:
        print(f"Gemini API call failed: {e}")
        return ""


def _get_fallback_response(user_query: str) -> str:
    """Return appropriate fallback response for out-of-scope queries."""
    greetings = ["hello", "hi", "hey", "good morning", "good evening", "namaste"]
    if any(greeting in user_query.lower() for greeting in greetings):
        return "Hello! I'm here to help you with legal and justice-related queries. How can I assist you with court services, legal procedures, or government services today?"
    
    bot_questions = ["what is your name", "who are you", "what are you", "your name"]
    if any(question in user_query.lower() for question in bot_questions):
        return "I'm the Department of Justice chatbot, designed to help citizens with legal queries, court procedures, and government services. How can I assist you with legal matters today?"
    
    return ("I'm designed to help with legal and justice-related queries. I can assist you with:\n"
            "• Court procedures and case status\n"
            "• Filing complaints (consumer, cyber crime, police)\n"
            "• Legal aid and free legal services\n"
            "• Document-related issues (Aadhaar, licence, etc.)\n"
            "• Land and family disputes\n\n"
            "Please ask me about any legal or government service you need help with.")


async def generate_bot_response(user_query: str, db, chat_id: str = None) -> str:
    """Generate bot response with confidence threshold and out-of-scope detection."""
    
    # Step 1: Fetch conversation history if chat_id is provided (do this first!)
    conversation_history: List[Tuple[str, str]] = []
    has_history = False
    if chat_id:
        try:
            messages = []
            async for doc in db.messages.find({"chatId": ObjectId(chat_id)}).sort("timestamp", 1):
                # Convert sender to role format expected by Gemini
                role = "user" if doc.get("sender") == "user" else "model"
                messages.append((role, doc.get("text", "")))
            
            # Remove the last message (the current user message we just inserted)
            if messages:
                messages = messages[:-1]
            
            # Only use the last 10 messages to avoid exceeding token limits
            conversation_history = messages[-10:] if len(messages) > 10 else messages
            has_history = len(conversation_history) > 0
        except Exception as e:
            print(f"Error fetching conversation history: {e}")
    
    # Step 2: Check if query is legal-related (skip if we have conversation history)
    if not has_history and not _is_legal_query(user_query):
        return _get_fallback_response(user_query)
    
    # Step 3: Vector search in knowledge_base.txt
    matches = await _vector_search(user_query, top_k=5)
    if not matches:
        # If we have conversation history, still try to use Gemini with context
        if has_history and _gemini_client is not None:
            gemini_response = await run_gemini_generation(user_query, "", conversation_history)
            if gemini_response and len(gemini_response.split()) >= 5:
                return gemini_response
        return _get_fallback_response(user_query)

    # Step 4: Check confidence threshold on the best match
    best_score = matches[0][1]
    if best_score < MIN_CONFIDENCE_THRESHOLD:
        # If we have conversation history, still try to use Gemini with context
        if has_history and _gemini_client is not None:
            gemini_response = await run_gemini_generation(user_query, "", conversation_history)
            if gemini_response and len(gemini_response.split()) >= 5:
                return gemini_response
        return _get_fallback_response(user_query)

    # Step 5: Filter and rank chunks
    filtered: List[Tuple[str, float, str]] = []
    for chunk, score in matches:
        cleaned = _clean_chunk_text(chunk)
        if len(cleaned.split()) >= 3:
            filtered.append((chunk, score, cleaned))
    
    def _token_set(s: str) -> set:
        toks = [t.lower() for t in re.split(r"\W+", s) if len(t) > 2]
        return set(toks)

    q_tokens = _token_set(user_query)
    ranked: List[Tuple[str, float, str, float]] = []
    
    for chunk, score, cleaned in filtered:
        chunk_tokens = _token_set(cleaned)
        if not chunk_tokens:
            overlap_frac = 0.0
        else:
            overlap_frac = len(q_tokens & chunk_tokens) / max(1, len(q_tokens))
        
        # Boost for URL-related queries
        url_boost = 0.0
        if any(word in user_query.lower() for word in ["url", "link", "website", "portal", "tell me the"]):
            if any(word in cleaned.lower() for word in ["http", "www", ".gov", ".in", ".com", "portal"]):
                url_boost = 0.3
        
        # Boost for exact keyword matches
        keyword_boost = 0.0
        important_keywords = {"cyber", "crime", "consumer", "complaint", "aadhaar", "licence", "legal", "aid"}
        if q_tokens & important_keywords:
            if chunk_tokens & important_keywords:
                keyword_boost = 0.2
        
        composite = 0.6 * score + 0.2 * overlap_frac + url_boost + keyword_boost
        ranked.append((chunk, score, cleaned, composite))

    ranked.sort(key=lambda x: x[3], reverse=True)

    if not ranked or ranked[0][3] < MIN_COMPOSITE_THRESHOLD:
        # If we have conversation history, still try to use Gemini with context
        if has_history and _gemini_client is not None:
            gemini_response = await run_gemini_generation(user_query, "", conversation_history)
            if gemini_response and len(gemini_response.split()) >= 5:
                return gemini_response
        return _get_fallback_response(user_query)

    # Step 6: Try Gemini generation with the best context(s) and conversation history
    if ranked:
        # Use top 2 chunks for better context
        top_contexts = [chunk[2] for chunk in ranked[:2]]
        combined_context = "\n\n".join(top_contexts)
        
        # Try Gemini API first
        if _gemini_client is not None:
            gemini_response = await run_gemini_generation(user_query, combined_context, conversation_history)
            if gemini_response and len(gemini_response.split()) >= 5:
                return gemini_response

        # Fallback to returning cleaned context if Gemini fails
        top_cleaned = ranked[0][2]
        if top_cleaned:
            # Extract key sentences
            sents = re.split(r'(?<=[.!?])\s+', top_cleaned)
            good_sents = [s for s in sents if len(s.split()) >= 3]
            
            if good_sents:
                # Return first 2-3 sentences that contain useful information
                result = " ".join(good_sents[:3]).strip()
                if len(result) > 20:  # Ensure it's substantial
                    return result[:800]

    # Step 7: Fallback to DB-stored FAQs (legacy support)
    try:
        fetched: List[Tuple[str, str]] = []
        async for doc in db.faqs.find({}):
            fetched.append((doc.get("question", ""), doc.get("answer", "")))
        if fetched and _embed_model is not None:
            qs = [q for q, _ in fetched]
            q_embs = _embed_model.encode(qs, convert_to_tensor=True, normalize_embeddings=True)
            query_emb = _embed_model.encode(user_query, convert_to_tensor=True, normalize_embeddings=True)
            scores = util.cos_sim(query_emb, q_embs)[0]
            best_idx = int(scores.argmax())
            best_score = float(scores[best_idx])
            if best_score >= 0.40:
                return fetched[best_idx][1]
    except Exception:
        pass

    # Final fallback
    return _get_fallback_response(user_query)


async def seed_default_faqs(db) -> None:
    return