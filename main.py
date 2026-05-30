import os
import re
import json
import random
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Misinformation Spread Analyser API",
    description="Backend API for real-time news fact-checking and spread estimation",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try importing generative AI and duckduckgo search
GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    pass

DDG_AVAILABLE = False
try:
    from duckduckgo_search import DDGS
    DDG_AVAILABLE = True
except ImportError:
    pass

# Helper to determine if we are in Mock Mode
def get_api_status() -> Dict[str, Any]:
    gemini_key = os.getenv("GEMINI_API_KEY")
    factcheck_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    
    is_gemini_ok = bool(gemini_key and GEMINI_AVAILABLE)
    is_factcheck_ok = bool(factcheck_key)
    
    # We are in live mode if at least Gemini is configured
    mode = "Live" if is_gemini_ok else "Mock"
    
    return {
        "gemini_configured": is_gemini_ok,
        "factcheck_configured": is_factcheck_ok,
        "mode": mode,
        "ddg_installed": DDG_AVAILABLE,
        "gemini_installed": GEMINI_AVAILABLE
    }

# ----------------- MOCK DATA GENERATION -----------------
# Generate deterministic pseudo-random values based on a query string hash.
# This ensures that querying the exact same claim returns consistent mock data.
def get_deterministic_seed(text: str) -> int:
    h = hashlib.sha256(text.lower().strip().encode('utf-8')).hexdigest()
    return int(h[:8], 16)

def generate_mock_analysis(query: str) -> Dict[str, Any]:
    seed = get_deterministic_seed(query)
    random.seed(seed)
    
    # Clean the query for matching templates
    q_clean = query.lower()
    
    # Pre-defined templates for fun/interactive testing of common tropes
    if any(k in q_clean for k in ["moon", "apollo", "space", "cheese"]):
        verdict = "FALSE"
        trust_score = random.randint(5, 15)
        explanation = (
            "The claim that Apollo moon landings were faked or that the Moon is not a solid celestial body is completely baseless. "
            "Extensive photographic evidence, laser ranging retroreflectors left on the surface, and over 382 kilograms of moon rocks "
            "brought back to Earth—which have been independently verified by scientists worldwide—conclusively prove the landings were real. "
            "Conspiracy theories regarding this matter often rely on misinterpretations of photographic physics and space telemetry."
        )
        sources = [
            {"title": "NASA Apollo Landing Missions Overview", "url": "https://www.nasa.gov/mission_pages/apollo/index.html", "publisher": "NASA", "rating": "Verified Truth"},
            {"title": "How We Know the Moon Landings Aren't Faked", "url": "https://www.space.com/apollo-moon-landing-conspiracy-theories.html", "publisher": "Space.com", "rating": "Fact-Checked"}
        ]
        spread = {"X / Twitter": 45, "Reddit": 25, "Facebook": 15, "YouTube": 10, "TikTok": 3, "Instagram": 2}
        velocity = "Low"
        
    elif any(k in q_clean for k in ["alien", "ufo", "roswel", "area 51"]):
        verdict = "UNVERIFIED"
        trust_score = random.randint(35, 55)
        explanation = (
            "While the government has acknowledged UAPs (Unidentified Anomalous Phenomena), there is currently no publicly available, "
            "rigorous scientific proof confirming that these objects are of extraterrestrial origin. "
            "Declassified reports indicate many sightings correspond to weather balloons, airborne clutter, or experimental military aircraft. "
            "Investigation is ongoing by NASA and the Pentagon's AARO, making the extraterrestrial claim unverified."
        )
        sources = [
            {"title": "DoD AARO Official Reports on UAPs", "url": "https://www.aaro.mil/", "publisher": "Department of Defense", "rating": "Official Investigation"},
            {"title": "NASA UAP Independent Study Team Report", "url": "https://science.nasa.gov/uap", "publisher": "NASA", "rating": "Scientific Analysis"}
        ]
        spread = {"X / Twitter": 30, "Reddit": 35, "Facebook": 10, "YouTube": 15, "TikTok": 7, "Instagram": 3}
        velocity = "Medium"
        
    elif any(k in q_clean for k in ["vaccine", "covid", "corona", "health", "cure"]):
        verdict = "MISLEADING"
        trust_score = random.randint(18, 30)
        explanation = (
            "The claim exaggerates or misrepresents medical science. Standard peer-reviewed literature confirms vaccines are highly monitored, "
            "safe, and effective at preventing severe illness. Isolated side-effects do exist but are extremely rare. "
            "Out-of-context statistics are commonly weaponized to create fear, leading to high spread velocity on visual social platforms."
        )
        sources = [
            {"title": "COVID-19 Vaccine Safety & Efficacy Facts", "url": "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/covid-19-vaccines", "publisher": "WHO", "rating": "Peer-reviewed Fact"},
            {"title": "Fact-Checking Vaccine Side Effect Rumors", "url": "https://www.factcheck.org/vaccine-misinformation/", "publisher": "FactCheck.org", "rating": "False Claims Debunked"}
        ]
        spread = {"Facebook": 35, "X / Twitter": 25, "TikTok": 20, "Reddit": 10, "Instagram": 8, "YouTube": 2}
        velocity = "High"
        
    elif any(k in q_clean for k in ["bitcoin", "crypto", "elon", "giveaway", "free", "rich"]):
        verdict = "FALSE"
        trust_score = random.randint(1, 5)
        explanation = (
            "This is a common financial scam. Prominent figures (like Elon Musk, Vitalik Buterin, or popular influencers) do not host "
            "'double your money' cryptocurrency giveaways. These schemes use hijacked accounts, deepfakes, or bot networks "
            "to drive victims to fraudulent landing pages where their deposited funds are permanently stolen."
        )
        sources = [
            {"title": "FTC Alerts on Cryptocurrency Giveaway Scams", "url": "https://consumer.ftc.gov/articles/what-know-about-cryptocurrency-scams", "publisher": "FTC", "rating": "Scam Alert"},
            {"title": "How to Identify Fake Social Media Giveaways", "url": "https://www.snopes.com/fact-check/elon-musk-bitcoin-giveaway/", "publisher": "Snopes", "rating": "Fake"}
        ]
        spread = {"X / Twitter": 50, "TikTok": 20, "YouTube": 15, "Facebook": 10, "Instagram": 4, "Reddit": 1}
        velocity = "Critical"
        
    else:
        # Default fallback mockup for arbitrary queries
        verdicts = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
        # Seeded weights: True (30%), False (40%), Misleading (20%), Unverified (10%)
        verdict = random.choices(verdicts, weights=[30, 40, 20, 10])[0]
        
        if verdict == "TRUE":
            trust_score = random.randint(85, 98)
            explanation = (
                f"The claim '{query}' is substantiated by primary documentation and reports from reputable news agencies. "
                "Cross-referencing verified journalists and academic databases reveals aligned timelines and credible sources. "
                "No signs of media manipulation or coordinated disinformation campaigns were detected for this claim."
            )
            velocity = "Low"
        elif verdict == "FALSE":
            trust_score = random.randint(2, 19)
            explanation = (
                f"The claim '{query}' is factually incorrect and has been debunked. "
                "Investigation reveals that the evidence cited in support of this statement is fabricated, taken out of context, "
                "or misattributed. Major media outlets and independent organizations have verified this as an active piece of misinformation."
            )
            velocity = "High"
        elif verdict == "MISLEADING":
            trust_score = random.randint(20, 59)
            explanation = (
                f"The claim '{query}' contains a kernel of truth but is surrounded by critical exaggerations, incorrect context, "
                "or biased editing designed to distort reality. Viewers are urged to read full contextual breakdowns rather than "
                "headlines, as important caveats have been omitted from the viral claim."
            )
            velocity = "Medium"
        else:
            trust_score = random.randint(40, 70)
            explanation = (
                f"Current reports regarding '{query}' are inconclusive. Major reporting agencies have noted claims, but "
                "independent, verifiable evidence remains scarce. The topic is under active debate, and users should "
                "treat early social rumors with extreme skepticism until official statements are released."
            )
            velocity = "Medium"
            
        sources = [
            {"title": f"Independent Fact-check on '{query[:30]}...'", "url": "https://www.reuters.com/fact-check/", "publisher": "Reuters Fact Check", "rating": verdict.capitalize()},
            {"title": f"Media Bias & Fact-checking Report", "url": "https://mediabiasfactcheck.com/", "publisher": "Media Bias Fact Check", "rating": "Contextual Source"}
        ]
        
        # Distribute spread randomly summing to 100
        platforms = ["X / Twitter", "Reddit", "Facebook", "YouTube", "TikTok", "Instagram"]
        raw_spread = [random.randint(5, 50) for _ in range(6)]
        total = sum(raw_spread)
        normalized = [round((val / total) * 100) for val in raw_spread]
        # Adjust rounding errors
        normalized[0] += (100 - sum(normalized))
        spread = {platforms[i]: normalized[i] for i in range(6)}

    # Ensure spread is sorted descending
    sorted_spread = dict(sorted(spread.items(), key=lambda item: item[1], reverse=True))

    return {
        "query": query,
        "verdict": verdict,
        "trust_score": trust_score,
        "explanation": explanation,
        "sources": sources,
        "platform_spread": sorted_spread,
        "spread_velocity": velocity,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "Mock Data (API Keys Not Configured)"
    }

# ----------------- LIVE DATA GATHERING -----------------
def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    if not DDG_AVAILABLE:
        return []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(keywords=query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                }
                for r in results
            ]
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
        return []

def query_google_factcheck(query: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key:
        return []
    
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        "query": query,
        "key": api_key,
        "languageCode": "en"
    }
    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code == 200:
            data = response.json()
            claims = data.get("claims", [])
            formatted_claims = []
            for c in claims:
                reviews = c.get("claimReview", [])
                if not reviews:
                    continue
                # Aggregate formatting
                for r in reviews:
                    formatted_claims.append({
                        "claim_text": c.get("claimText", ""),
                        "claimant": c.get("claimant", "Unknown"),
                        "publisher": r.get("publisher", {}).get("name", "Fact Checker"),
                        "url": r.get("url", ""),
                        "rating": r.get("textualRating", "Unknown"),
                        "title": r.get("title", "Fact Check Review")
                    })
            return formatted_claims
    except Exception as e:
        print(f"Google FactCheck API failed: {e}")
    return []

def estimate_live_spread(query: str, search_results: List[Dict[str, str]]) -> Dict[str, int]:
    # Set default distribution based on search query text hashing (stable fallback)
    seed = get_deterministic_seed(query)
    random.seed(seed)
    
    platforms = {
        "X / Twitter": {"domains": ["twitter.com", "x.com"], "keywords": ["twitter", "tweet", "post on x"], "points": 0},
        "Reddit": {"domains": ["reddit.com"], "keywords": ["reddit", "subreddit", "r/"], "points": 0},
        "Facebook": {"domains": ["facebook.com"], "keywords": ["facebook", "fb.com", "fb share"], "points": 0},
        "YouTube": {"domains": ["youtube.com", "youtu.be"], "keywords": ["youtube", "yt video"], "points": 0},
        "TikTok": {"domains": ["tiktok.com"], "keywords": ["tiktok", "tok video", "trending on tiktok"], "points": 0},
        "Instagram": {"domains": ["instagram.com"], "keywords": ["instagram", "insta post", "ig post"], "points": 0}
    }
    
    # Run scoring on search engine snippets and URLs
    total_matches = 0
    for r in search_results:
        url = r.get("url", "").lower()
        title_snippet = (r.get("title", "") + " " + r.get("snippet", "")).lower()
        
        for name, meta in platforms.items():
            # Domain match in URL gets high score
            if any(domain in url for domain in meta["domains"]):
                meta["points"] += 12
                total_matches += 12
            # Keyword mention in title/body text gets medium score
            if any(kw in title_snippet for kw in meta["keywords"]):
                meta["points"] += 4
                total_matches += 4

    # If we have matches, normalize them to percentages.
    if total_matches > 0:
        spread = {}
        for name, meta in platforms.items():
            # Add a base rate of 2 points to ensure all platforms have visual presence
            pts = meta["points"] + 2
            spread[name] = pts
        
        # Normalize
        total = sum(spread.values())
        normalized = {}
        for name, val in spread.items():
            normalized[name] = round((val / total) * 100)
            
        # Repair rounding error
        err = 100 - sum(normalized.values())
        first_key = list(normalized.keys())[0]
        normalized[first_key] += err
    else:
        # Fallback to realistic random distribution based on seeded query hash
        # Different claims will naturally spread on different platforms based on topic keywords
        weights = [15, 15, 15, 15, 15, 15]
        q_clean = query.lower()
        if "video" in q_clean or "dance" in q_clean or "viral" in q_clean:
            weights = [10, 5, 10, 20, 35, 20] # Video focus (TikTok, YT, IG)
        elif "politics" in q_clean or "news" in q_clean or "breaking" in q_clean:
            weights = [45, 15, 20, 10, 5, 5]  # Political focus (X, FB, Reddit)
        elif "meme" in q_clean or "joke" in q_clean:
            weights = [25, 40, 5, 5, 10, 15]  # Meme focus (Reddit, X, IG)
        
        raw_spread = [random.randint(1, 10) * w for w in weights]
        tot = sum(raw_spread)
        normalized = {}
        for i, name in enumerate(platforms.keys()):
            normalized[name] = round((raw_spread[i] / tot) * 100)
        # Repair rounding error
        err = 100 - sum(normalized.values())
        normalized[list(normalized.keys())[0]] += err
        
    # Sort descending
    return dict(sorted(normalized.items(), key=lambda item: item[1], reverse=True))

def run_live_analysis(query: str) -> Dict[str, Any]:
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    # 1. Query Google Fact Check API first
    factcheck_results = query_google_factcheck(query)
    
    # 2. Query DuckDuckGo for context grounding
    search_results = search_duckduckgo(query, max_results=12)
    
    # 3. Estimate social spread based on search results
    platform_spread = estimate_live_spread(query, search_results)
    
    # Determine velocity based on top platform score
    top_score = list(platform_spread.values())[0]
    if top_score > 40:
        velocity = "Critical"
    elif top_score > 28:
        velocity = "High"
    elif top_score > 18:
        velocity = "Medium"
    else:
        velocity = "Low"

    # Assemble structured text of search results for Gemini context
    context_str = ""
    for idx, r in enumerate(search_results[:8]):
        context_str += f"[{idx+1}] Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n\n"
        
    fact_check_context = ""
    for idx, f in enumerate(factcheck_results[:4]):
        fact_check_context += f"Fact-checker: {f['publisher']} - Rating: {f['rating']} - Claim: {f['claim_text']}\n"
        
    current_date_str = datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""
    You are an expert misinformation analyst and fact-checker. 
    Today's date is {current_date_str}. Use this date to evaluate all relative time claims (e.g. 'tomorrow', 'this year', '2026').
    
    Analyze the following query / claim: "{query}"
    
    We found the following pre-scraped search results (which may be empty):
    {context_str}
    
    We found the following official database factcheck reviews:
    {fact_check_context}
    
    You have a live Google Search tool enabled. If you need more information to verify this claim (for example, if the claim is about who is playing in the IPL 2026 final, or the current status of an event), you MUST use the search tool to run searches like "IPL 2026 final teams schedule" or "who is playing the IPL final 2026" to verify the actual facts. Do not guess, and do not say it is unverified if a search can give you the definitive answer!
    
    If the claim is contradicted by official news, schedules, or results (e.g., the claim says Team X is playing the final, but search results show Team Y and Team Z are the actual finalists), mark the claim as FALSE, and detail the true facts in your explanation.
    
    Special Rule for Attributed Quotes ("X claimed Y" or "X said Y"):
    If the query is structured as "Person/Organization X claimed that Y", you must check BOTH:
    1. Did Person/Organization X actually make that claim? (Attribution check)
    2. Is the content of the claim Y itself true, false, or misleading? (Substance check)
    In your explanation, address both:
    - First, confirm if they actually made the statement (e.g. "Yes, X did make this statement on CBS News on Date...").
    - Second, analyze the truth/misleading nature of the statement itself (e.g. "However, the statement itself is misleading because...").
    - Make sure the overall verdict reflects the factual accuracy of the substance (Y) but clearly separates it from the attribution in the explanation.
    
    Based on all available information, perform a rigorous fact-check.
    You must output a valid JSON object matching the following structure EXACTLY:
    {{
      "verdict": "TRUE" | "FALSE" | "MISLEADING" | "UNVERIFIED",
      "trust_score": <integer between 0 and 100, where 0 is complete lie/scam and 100 is verified facts>,
      "explanation": "<detailed, objective, multi-sentence markdown paragraph explaining why the claim is true, false, misleading, or unverified. Mention the exact date, key findings from searches, and the true facts.>"
    }}
    
    Rules:
    1. Be highly objective and scientific.
    2. Do NOT mention HTML tags. Use markdown for bolding.
    3. Ensure the JSON is valid. Output ONLY the JSON block. Do not wrap in ```json ``` markdown blocks.
    """

    # 4. Call Gemini using the new google-genai SDK (with smart multi-model fallback)
    try:
        client = genai.Client(api_key=gemini_key)
        
        # Query Google to see what models this API key actually supports
        models_to_try = []
        try:
            listed = list(client.models.list())
            for m in listed:
                name = m.name
                if name.startswith("models/"):
                    name = name[7:]
                models_to_try.append(name)
            print(f"API key supports models: {models_to_try}")
        except Exception as list_err:
            print(f"Could not list models: {list_err}. Using hardcoded fallbacks.")
            
        # Hardcoded fallback list in order of preference
        fallbacks = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]
        for fb in fallbacks:
            if fb not in models_to_try:
                models_to_try.append(fb)
                
        # Configure Google Search Grounding tool (enables direct real-time Google search by Gemini)
        grounding_config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        # Try models in sequence until one succeeds
        response = None
        last_model_error = None
        for m_name in models_to_try:
            try:
                print(f"Attempting fact analysis with: {m_name}...")
                response = client.models.generate_content(
                    model=m_name,
                    contents=prompt,
                    config=grounding_config
                )
                print(f"Success! Model {m_name} generated the verification analysis.")
                break
            except Exception as model_e:
                print(f"Model {m_name} failed: {model_e}")
                last_model_error = model_e
                
        if response is None:
            raise last_model_error
            
        text_response = response.text.strip()
        
        # Clean response and extract JSON block robustly (find content between first '{' and last '}')
        cleaned_response = text_response
        first_brace = cleaned_response.find('{')
        last_brace = cleaned_response.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned_response = cleaned_response[first_brace:last_brace + 1]
        
        # Parse JSON
        result = json.loads(cleaned_response)
    except Exception as e:
        print(f"Gemini API invocation failed: {e}. Falling back to rule-based parser.")
        # Rule-based fallback if LLM parser failed or returned bad format
        if factcheck_results:
            first_fact = factcheck_results[0]
            rating_lower = first_fact["rating"].lower()
            if "false" in rating_lower or "fake" in rating_lower or "incorrect" in rating_lower:
                verdict = "FALSE"
                score = 10
            elif "true" in rating_lower or "correct" in rating_lower or "verified" in rating_lower:
                verdict = "TRUE"
                score = 90
            elif "misleading" in rating_lower or "half true" in rating_lower or "exaggerated" in rating_lower:
                verdict = "MISLEADING"
                score = 35
            else:
                verdict = "UNVERIFIED"
                score = 50
            explanation = f"Fact-checked by {first_fact['publisher']}. Rating details: '{first_fact['rating']}'. Title: '{first_fact['title']}'."
        else:
            verdict = "UNVERIFIED"
            score = 45
            explanation = f"Unable to reach LLM reasoning models. Details: {str(e)}"
        result = {"verdict": verdict, "trust_score": score, "explanation": explanation}

    # Extract dynamic grounding metadata from the successful Gemini model response
    grounding_sources = []
    try:
        if response and response.candidates and response.candidates[0].grounding_metadata:
            meta = response.candidates[0].grounding_metadata
            chunks = getattr(meta, "grounding_chunks", [])
            for c in chunks:
                web = getattr(c, "web", None)
                if web:
                    title = getattr(web, "title", "Google Search Reference")
                    uri = getattr(web, "uri", "")
                    if uri and not any(src["url"] == uri for src in grounding_sources):
                        domain = uri.split("/")[2] if "/" in uri else "google.com"
                        grounding_sources.append({
                            "title": title,
                            "url": uri,
                            "publisher": domain.replace("www.", ""),
                            "rating": "Grounded News Link"
                        })
    except Exception as meta_err:
        print(f"Failed to parse Google Search grounding metadata: {meta_err}")

    # Map sources to return to UI
    sources_to_return = []
    
    # Add Google Search grounding sources
    sources_to_return.extend(grounding_sources)
    
    # Add Google FactCheck reviews first
    for f in factcheck_results[:3]:
        sources_to_return.append({
            "title": f["title"],
            "url": f["url"],
            "publisher": f["publisher"],
            "rating": f["rating"]
        })
        
    # Append high quality general news search results
    for s in search_results[:4]:
        # Avoid duplicating URLs
        if any(src["url"] == s["url"] for src in sources_to_return):
            continue
        # Extract site name
        domain = s["url"].split("/")[2] if "/" in s["url"] else "Web Link"
        sources_to_return.append({
            "title": s["title"],
            "url": s["url"],
            "publisher": domain.replace("www.", ""),
            "rating": "General Context"
        })

    return {
        "query": query,
        "verdict": result.get("verdict", "UNVERIFIED").upper(),
        "trust_score": result.get("trust_score", 50),
        "explanation": result.get("explanation", "No explanation compiled."),
        "sources": sources_to_return,
        "platform_spread": platform_spread,
        "spread_velocity": velocity,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "Live AI Grounded API"
    }

# ----------------- ENDPOINTS -----------------
@app.get("/api/status")
def status():
    return get_api_status()

@app.get("/api/analyze")
def analyze(q: str = Query(..., min_length=2, description="Claim or URL to analyze")):
    status_info = get_api_status()
    
    if status_info["mode"] == "Mock":
        # Run mock engine
        return generate_mock_analysis(q)
    else:
        # Run live engine
        return run_live_analysis(q)

# Fallback: Serve static index.html for UI SPA route
@app.get("/")
def read_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))

# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

if __name__ == "__main__":
    import uvicorn
    # Read environment configs or use default
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Starting Misinformation Analyser on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
