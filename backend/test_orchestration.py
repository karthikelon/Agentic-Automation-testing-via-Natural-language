import asyncio
import os
import json
from dotenv import load_dotenv
from browser_service import BrowserService
from agent_core import AgentCore

async def run_diagnostic_test():
    load_dotenv()
    print("Starting Agentic Orchestration Diagnostic...")
    
    browser = BrowserService()
    agent = AgentCore()
    
    try:
        await browser.start()
        print("Browser Started")
        
        goal = "Go to example.com and check the page title."
        history = []
        
        print("Sensing...")
        screenshot = await browser.get_screenshot_base64()
        ax_tree = await browser.get_accessibility_snapshot()
        events = browser.get_and_clear_events()
        
        # Think
        print("Thinking...")
        decision = await agent.analyze_state_and_decide(
            screenshot, 
            goal, 
            history, 
            ax_tree=ax_tree, 
            events=events,
            use_pro=True
        )
        
        print(f"Agent Decision: {json.dumps(decision, indent=2)}")
        
        if "type" in decision:
            print("OK: Orchestration Loop Working Perfectly!")
        else:
            print("ERR: Invalid Decision Format")
            
    except Exception as e:
        print(f"ERR: Diagnostic Failed: {e}")
    finally:
        await browser.stop()
        print("Diagnostic Finished")

if __name__ == "__main__":
    asyncio.run(run_diagnostic_test())
