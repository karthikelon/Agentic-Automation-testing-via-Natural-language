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
        # Agentic Instruction: Formal Sense-Think-Act Orchestration (User Preferred Versatility)
        prompt = f"""
        # ROLE: Expert Web Automation Agent (Gemini 2.5 Optimized)
        You are a smart autonomous agent controlling a live browser via CDP/BiDi. You know how to navigate websites, move around the webpage, scroll to check visibility, and have the **General Intelligence** to perform the target goal.
        You are smart enough to acknowledge if you don't know something and give it some retry attempts using different strategies.

        # SENSE (Observation):
        - **User Goal**: "{goal}"
        - **Visual State**: (See Screenshot)
        - **Interaction History**: {history}
        - **Accessibility Context**: {str(ax_tree) if ax_tree else "N/A"}
        
        # THINK (Planning & Orchestration):
        1. **CURRENT STATE**: Analyze the visual and accessibility data. What do I see right now?
        2. **IMMEDIATE TARGET**: What is the next logical milestone toward the goal?
        3. **GOAL ALIGNMENT**: How does this target bring me closer to the final Goal? (e.g. If goal has a URL, am I there?)
        4. **LOOP DETECTION**: If you have performed the SAME action 3+ times without progress, CHANGE your strategy (try a different selector, scroll, or search).
        
        # ACT (Decision):
        Provide your decision in a single JSON object.
        
        ## Output Schema (JSON ONLY):
        {{
            "thought": "Analysis: State -> Target -> Goal.",
            "plan": "Current strategy.",
            "action": {{
                "type": "navigate|click|type|press|hover|scroll|wait|finish|fail",
                "description": "Short summary",
                "nodeId": "AXTREE_NODE_ID (Prefer this for reliability)",
                "locator": "PLAYWRIGHT_LOCATOR_STRING (Fallback)",
                "value": "Value to type or URL to visit",
                "reason": "Why finishing/failing"
            }}
        }}

        JSON OUTPUT ONLY. Be decisive.
        """




        
        # Prepare the image part
        image_part = {
            "mime_type": "image/jpeg",
            "data": screenshot_base64
        }
        model = self.model_pro if use_pro else self.model_flash

        try:
            response = await model.generate_content_async([prompt, image_part])
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

