import asyncio
import json
import os
import traceback
from browser_service import BrowserService
from agent_core import AgentCore
from reporting import ReportManager

class Orchestrator:
    def __init__(self, websocket, report_dir_base, browser_service):
        self.websocket = websocket
        self.report_dir_base = report_dir_base
        
        # Services
        self.browser_service = browser_service # Injected Singleton
        self.agent_core = AgentCore()
        self.report_manager = ReportManager()
        
        # State
        self.current_goal = None
        self.task_history = []
        self.active_task = None # The asyncio.Task for the main loop
        self.is_running = False
        
        # Concurrency
        self.msg_queue = asyncio.Queue()

    async def start(self, goal: str, step_by_step: bool = False):
        """Starts a new orchestration session."""
        if self.is_running:
            await self.stop("Restarting...")
            
        self.current_goal = goal
        self.task_history = []
        self.is_running = True
        
        # Start Browser
        await self.browser_service.start()
        await self.send_log("Neural Link Established. Browser Ready.")
        
        # Create Report Session
        self.report_manager.start_session(goal)
        await self.send_log(f"Orchestrating goal: {goal}")
        
        # Start the Loop Task
        self.active_task = asyncio.create_task(self._run_loop(step_by_step))
        return self.active_task

    async def stop(self, reason="User Stopped"):
        """Stops the current session immediately."""
        self.is_running = False
        if self.active_task and not self.active_task.done():
            print(f"Orchestrator: Cancelling task due to: {reason}")
            self.active_task.cancel()
            try:
                await self.active_task
            except asyncio.CancelledError:
                pass
        
        # Ensure we clean up browser? Or keep it open?
        # Typically we keep browser open for state inspection, but stop the loop.
        # But for full reset, we might want to ensure browser is in a known state.
        # For now, we just stop the loop.
        await self.send_log(f"Execution Interrupted: {reason}")
        self.report_manager.end_session("stopped")
        await self.send_report_link()

    async def process_message(self, raw_msg: str):
        """Handles incoming WebSocket messages."""
        try:
            msg = json.loads(raw_msg)
            msg_type = msg.get("type")
            
            if msg_type == "stop":
                await self.stop("User Clicked Stop")
            elif msg_type == "next_step":
                # Put in queue for the loop to consume if paused
                await self.msg_queue.put(msg)
        except Exception as e:
            print(f"Orchestrator Message Error: {e}")

    async def _run_loop(self, step_by_step: bool):
        """The main Sense-Think-Act loop."""
        try:
            while self.is_running:
                # PHASE 1: SENSE
                screenshot_b64 = await self.browser_service.get_screenshot_base64()
                ax_tree = await self.browser_service.get_accessibility_snapshot()
                events = self.browser_service.get_and_clear_events()
                
                await self.send_state(screenshot_b64, events)

                # PHASE 2: THINK
                await self.send_log("Thinking...")
                
                # Check cancellation before expensive API call
                if not self.is_running: break

                use_pro = (len(self.task_history) == 0 or (self.task_history and self.task_history[-1].get("action", {}).get("type") == "fail"))
                
                # AI Call (cancellable via self.active_task.cancel())
                full_decision = await self.agent_core.analyze_state_and_decide(
                    screenshot_b64, self.current_goal, self.task_history, ax_tree=ax_tree, events=events, use_pro=use_pro
                )

                if full_decision.get("plan"):
                    await self.send_log(f"Plan: {full_decision['plan']}")
                
                decision = full_decision.get("action", {})
                thought = full_decision.get("thought", decision.get("description", "Moving forward..."))
                
                await self.websocket.send_json({
                    "type": "thought", 
                    "thought": f"[{'Gemini Pro' if use_pro else 'Gemini Flash'}] {thought}"
                })

                # PHASE 3: ACT
                action_type = decision.get("type")
                
                # Locator Debug
                if decision.get("locator"):
                    print(f"Orchestrator: Generated Locator (Backup): {decision.get('locator')}")

                # Log Step
                step_idx = len(self.task_history) + 1
                self.report_manager.log_step(step_idx, 
                                           {"url": self.browser_service.page.url if self.browser_service.page else "Unknown"}, 
                                           full_decision, 
                                           screenshot_b64)

                if action_type == "finish":
                    self.report_manager.end_session("success")
                    await self.send_report_link()
                    await self.websocket.send_json({"type": "success", "message": "Goal Achieved!"})
                    self.is_running = False
                    break
                
                elif action_type == "fail":
                    self.report_manager.end_session("failed")
                    await self.send_report_link()
                    await self.websocket.send_json({"type": "error", "message": f"Agent stopped: {decision.get('reason')}"})
                    self.is_running = False
                    break
                
                else:
                    desc = decision.get("description", f"Executing {action_type}")
                    await self.send_log(f"Executing: {desc}")
                    
                    # Execute Action (Cancellable)
                    val = decision.get("value") or decision.get("url") or decision.get("key")
                    node_id = decision.get("nodeId")
                    
                    await self.browser_service.execute_action(
                        action_type, decision.get("selector"), val, node_id=node_id
                    )
                    
                    self.task_history.append(full_decision)
                    
                    # Post-Action Sense
                    screenshot_b64 = await self.browser_service.get_screenshot_base64()
                    await self.send_state(screenshot_b64, self.browser_service.get_and_clear_events())

                    if step_by_step:
                        await self.websocket.send_json({"type": "pause", "message": "Step-by-Step Approval Needed."})
                        # Wait for next_step or stop
                        msg = await self.msg_queue.get()
                        if msg.get("type") == "stop":
                            break

        except asyncio.CancelledError:
            print("Orchestrator: Loop Cancelled cleanly.")
            raise # Propagate to ensure clean exit
        except Exception as e:
            print(f"Orchestrator Loop Error: {e}")
            traceback.print_exc()
            await self.websocket.send_json({"type": "error", "message": f"Critical Error: {str(e)}"})
        finally:
            # ALWAYS send report link if session ended
            self.is_running = False
            if self.report_manager.current_report_dir:
                await self.send_report_link()

    async def send_log(self, message: str):
        if self.websocket:
            await self.websocket.send_json({"type": "log", "message": message})

    async def send_state(self, screenshot, events):
        if self.websocket:
             await self.websocket.send_json({
                "type": "state", 
                "screenshot": screenshot,
                "url": self.browser_service.page.url if self.browser_service.page else "Unknown",
                "events": events
            })

    async def send_report_link(self):
        try:
            if not self.report_manager.current_report_dir:
                return
            report_url = f"http://localhost:8000/reports_files/{self.report_manager.current_report_dir.split(os.sep)[-1]}/index.html"
            print(f"Orchestrator: Sending Report URL: {report_url}")
            await self.websocket.send_json({"type": "report", "url": report_url})
        except Exception as e:
            print(f"Orchestrator: Failed to send report link: {e}")

    async def shutdown(self):
        # We do NOT stop the browser here anymore, as it is a global singleton.
        # This prevents the browser from closing just because the WS disconnected (e.g. page refresh).
        if self.is_running:
            await self.stop("Connection Lost")
