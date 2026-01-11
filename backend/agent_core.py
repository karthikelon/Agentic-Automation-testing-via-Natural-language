import os
import warnings
import json
from dotenv import load_dotenv

# Suppress the deprecation warning before import
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

import google.generativeai as genai

load_dotenv()

class AgentCore:
    def __init__(self):
        # Prefer GOOGLE_API_KEY as it's the standard for the SDK
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("CRITICAL: No API Key found in environment (checked GOOGLE_API_KEY and GEMINI_API_KEY)")
        else:
            print(f"AgentCore: Configuring SDK with key (ends in ...{api_key[-4:]})")
            genai.configure(api_key=api_key)
            self.model_pro = genai.GenerativeModel('gemini-2.5-pro')
            self.model_flash = genai.GenerativeModel('gemini-2.5-flash')
            print(f"AgentCore: Models initialized (2.5 Pro & Flash)")



    async def analyze_state_and_decide(self, screenshot_base64: str, goal: str, history: list, ax_tree: dict = None, events: dict = None, use_pro: bool = False):
        """
        Observes the screenshot and CDP data to decide the next action based on the goal.
        """
        
        # Agentic Instruction: Formal Sense-Think-Act Orchestration
        prompt = f"""
        # ROLE: Expert Web Automation Agent (Gemini 2.5 Flash Optimized)
        # CONTEXT: You are controlling a live browser via CDP/BiDi.
        
        # SENSE (Observation):
        - Goal: {goal}
        - Browser Events (CDP): {events}
        - Interaction History: {history}
        - Accessibility Tree (Protocol Data): {json.dumps(ax_tree, indent=2) if ax_tree else "N/A"}
        
        # THINK (Planning & Orchestration):
        1. **CURRENT STATE**: Analyze the visual and accessibility data. What do I see right now?
        2. **IMMEDIATE TARGET**: What is the next logical milestone toward the goal? (e.g., "Finding the product row", "Clicking the cart icon").
        3. **GOAL ALIGNMENT**: How does this target bring me closer to the final Goal?
        4. **LOOP DETECTION**: If you have performed the SAME action 3+ times without progress, CHANGE your strategy or FAIL.
        
        # ACT (Decision):
        Provide your decision in JSON.
        
        Output Schema:
        {{
          "plan": "Current high-level strategy",
          "thought": "State -> Target -> Goal reasoning",
          "action": {{
             "type": "navigate|click|type|press|hover|scroll|finish|fail",
             "nodeId": "AXTree nodeId (PREFER THIS)",
             "selector": "CSS selector (FALLBACK)",
             "url": "...",
             "value": "...",
             "description": "Short action summary"
          }}
        }}
        
        JSON OUTPUT ONLY.
        """




        
        # Prepare the image part
        image_part = {
            "mime_type": "image/jpeg",
            "data": screenshot_base64
        }
        model = self.model_pro if use_pro else self.model_flash

        try:
            response = model.generate_content([prompt, image_part])
            text_response = response.text.strip()
            # Basic cleanup if model wraps in code blocks
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()
                
            return json.loads(text_response)
        except Exception as e:
            print(f"Error in Agent Decision: {e}")
            return {"type": "fail", "reason": f"Agent error: {str(e)}", "description": "Error thinking"}

