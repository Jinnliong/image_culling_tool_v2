import ollama
import json
import re
import math
import os

def _safe_val(v, default=0):
    """Safely converts values to integer without crashing on strings or None."""
    try:
        if v is None: 
            return default
        val = float(v)
        if math.isnan(val): 
            return default
        return int(val)
    except Exception:
        return default

def analyze_image(base64_img, mode="Operation (My Work)"):
    """
    🦛 Project Hippocampus: Documentary Curator Engine v0.17.0
    Standards: 5W+1H Physical Evidence, 3-Plane Layering, Narrative Mood, Mo Lei Tou
    """
    
    prompt = f"""
    You are a veteran documentary photo editor and Magnum jury curator.
    Analyze this photograph using high-precision scoring (0-100).
    Never use safe round numbers (e.g., 60, 70, 80, 85). Output authentic, granular integers (e.g., 67, 74, 88, 93).

    ### 1. DOCUMENTARY JOURNALISM (5W + 1H EVIDENCE-LOCKED):
    Base all observations strictly on VISIBLE evidence in the frame—no speculative fiction:
    - WHO: Visible human presence, posture, gaze, gestures, hands, or human traces.
    - WHAT: Decisive physical action, interaction, or silent pause.
    - WHERE & WHEN: Environmental markers, architecture, lighting quality, time/weather cues.
    - WHY & HOW: Visual tension, relationship between subjects, or interaction with tools/space.

    ### 2. VISUAL ARCHITECTURE & LAYERING (45% Weight):
    - Depth Planes: Effective use of Foreground (context/lead-in), Midground (subject/action), and Background (stakes/setting).
    - Framing: Leading lines, frame-within-a-frame, geometry, camera angle, and negative space (Wu Wei).

    ### 3. MOOD & EMOTIONAL IMPACT (The Feeling):
    - Light & Shadow: Chiaroscuro, contrast, shadow falloff, and color harmony reinforcing the emotional gravity.
    - Visceral Atmosphere: Does it convey grit, quiet dignity, melancholy, tension, or resilience?

    ### 4. TECHNICAL RIGOR & SUBVERSION:
    - Sharpness: Acutance focused strictly on the narrative anchor (eyes, hands, main action).
    - Mo Lei Tou: Subtle street irony, visual collisions, deadpan contrast, or bittersweet absurdity.

    ### OUTPUT FORMAT (STRICT JSON ONLY):
    {{
      "Narrative_5W1H": "Who: [Subject/Posture] | What: [Action] | Where/When: [Visible Context] | Why/How: [Visual Tension]",
      "Composition_Critique": "Layering: [Foreground/Mid/Background] | Mood: [Atmosphere & Light Quality]",
      "Composition": 0-100,
      "Sharpness": 0-100,
      "Exposure": 0-100,
      "Impact": 0-100,
      "Creativity": 0-100,
      "Style": 0-100,
      "Narrative_Score": 0-100,
      "Mo_Lei_Tou": 0-100,
      "Competition_Status": "PASS or DQ",
      "Chinny_Roast": 0-100,
      "Privacy_Alert": "YES or NO"
    }}
    """

    try:
        response = ollama.chat(
            model='llava-phi3',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [base64_img]
            }],
            options={'temperature': 0.3}  # Lower temp keeps the 3.8B model grounded to visible pixels
        )
        
        raw_text = response['message']['content']
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        
        if json_match:
            data = json.loads(json_match.group())
            
            # --- SAFE NUMERICAL CASTING ---
            comp_val = _safe_val(data.get('Composition'))
            sharp_val = _safe_val(data.get('Sharpness'))
            exp_val = _safe_val(data.get('Exposure'))
            
            # --- WEIGHT ADJUSTMENT: COMPOSITION IS KING (45%) ---
            tech_score = int((comp_val * 0.45) + (sharp_val * 0.35) + (exp_val * 0.20))
            
            # Synthesize structured critique for the dashboard inspector
            n_part = data.get('Narrative_5W1H', '').strip()
            c_part = data.get('Composition_Critique', '').strip()
            full_critique = f"📖 **5W+1H:** {n_part}\n\n🎨 **Framing & Mood:** {c_part}" if (n_part or c_part) else data.get('Critique', '')

            return {
                "Tech Score": tech_score,
                "Composition": comp_val,
                "Sharpness": sharp_val,
                "Exposure": exp_val,
                "Narrative Score": _safe_val(data.get('Narrative_Score')),
                "Emotional Impact": _safe_val(data.get('Impact')),
                "Creativity": _safe_val(data.get('Creativity')),
                "Style": _safe_val(data.get('Style')),
                "Mo Lei Tou": _safe_val(data.get('Mo_Lei_Tou')),
                "Competition Status": str(data.get('Competition_Status', 'PASS')).strip().upper(),
                "Chinny Roast": _safe_val(data.get('Chinny_Roast')),
                "Privacy Alert": str(data.get('Privacy_Alert', 'NO')).strip().upper(),
                "Raw Reply": full_critique
            }
        return None
    except Exception as e:
        print(f"ai_engine error: {e}")
        return None

def categorize_photo(metrics, m_sharp, m_exp, m_comp, m_tech, m_narr, m_emo, m_creativity, m_style, m_moleitou=75):
    """
    🦛 Composition-First Triage Logic
    Hierarchy: Hard Discard -> Masterpiece -> Composition-Backed Maverick -> Tech Baseline -> Keeper Tiers
    """
    s = _safe_val(metrics.get('Sharpness'))
    e = _safe_val(metrics.get('Exposure'))
    c = _safe_val(metrics.get('Composition'))
    t = _safe_val(metrics.get('Tech Score'))
    n = _safe_val(metrics.get('Narrative Score'))
    emo = _safe_val(metrics.get('Emotional Impact'))
    creativity = _safe_val(metrics.get('Creativity'))
    style = _safe_val(metrics.get('Style'))
    moleitou = _safe_val(metrics.get('Mo Lei Tou'))
    
    comp_status = str(metrics.get('Competition Status', 'PASS')).strip().upper()
    
    # 1. HARD DISCARD (The Void)
    # Severe technical failure, complete absence of framing, or disqualified
    if s < m_sharp or c < (m_comp - 10) or comp_status == 'DQ':
        return "Discard"
    
    # 2. CROWN: THE MASTERPIECE
    # Flawless convergence of framing, documentary story, emotional mood, and technical execution
    if n >= m_narr and emo >= m_emo and c >= m_comp and t >= m_tech:
        return "Keeper_Masterpiece"
    
    # 3. THE SPARK: MAVERICK & MO LEI TOU (Requires Intentional Framing)
    # Subversive street satire or high visual creativity anchored by solid composition
    is_maverick_vibe = (moleitou >= m_moleitou) or (creativity >= m_creativity and style >= m_style)
    if is_maverick_vibe and c >= m_comp:
        return "Keeper_Maverick"
    
    # 4. TRIAGE: HUMAN REVIEW
    # High story potential or emotional mood, but technically flawed or compositionally loose
    if t < m_tech or c < m_comp:
        return "Review"
    
    # 5. KEEPER TIERS (Requires passing the composition baseline)
    if n >= m_narr:
        return "Keeper_Storyteller"
    
    if emo >= m_emo:
        return "Keeper_Mood"
    
    return "Keeper_Technical"