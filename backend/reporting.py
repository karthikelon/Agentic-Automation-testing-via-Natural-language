
import os
import json
import base64
import time
from datetime import datetime

class ReportManager:
    def __init__(self, base_dir="reports"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        
        self.current_report_dir = None
        self.report_data = {
            "session_id": "",
            "start_time": "",
            "goal": "",
            "status": "running",
            "steps": []
        }

    def start_session(self, goal):
        """Starts a new reporting session."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_goal = "".join([c if c.isalnum() else "_" for c in goal[:20]])
        session_id = f"{timestamp}_{safe_goal}"
        
        self.current_report_dir = os.path.join(self.base_dir, session_id)
        os.makedirs(self.current_report_dir, exist_ok=True)
        
        self.report_data = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "goal": goal,
            "status": "running",
            "steps": []
        }
        print(f"ReportManager: Started session {session_id}")

    def log_step(self, step_index, state, decision, screenshot_b64=None):
        """Logs a single step with screenshot and decision."""
        if not self.current_report_dir:
            return

        # Save screenshot to file
        screenshot_path = None
        if screenshot_b64:
            try:
                # Remove header if present
                if "," in screenshot_b64:
                    screenshot_b64 = screenshot_b64.split(",")[1]
                
                img_data = base64.b64decode(screenshot_b64)
                img_filename = f"step_{step_index}.jpg"
                img_path = os.path.join(self.current_report_dir, img_filename)
                
                with open(img_path, "wb") as f:
                    f.write(img_data)
                
                screenshot_path = img_filename # Relative path for JSON
            except Exception as e:
                print(f"ReportManager: Failed to save screenshot: {e}")

        step_record = {
            "step_index": step_index,
            "timestamp": datetime.now().isoformat(),
            "url": state.get("url", "unknown"),
            "screenshot": screenshot_path,
            "thought": decision.get("thought", ""),
            "plan": decision.get("plan", ""),
            "action": decision.get("action", {})
        }
        
        self.report_data["steps"].append(step_record)
        self._save_report()

    def end_session(self, status):
        """Finalizes the report with a status (success/failed/stopped)."""
        self.report_data["status"] = status
        self.report_data["end_time"] = datetime.now().isoformat()
        self._save_report()
        print(f"ReportManager: Session ended with status: {status}")

    def _save_report(self):
        """Writes the current report_data to report.json."""
        if not self.current_report_dir:
            return
            
        report_path = os.path.join(self.current_report_dir, "report.json")
        try:
            with open(report_path, "w") as f:
                json.dump(self.report_data, f, indent=2)
        except Exception as e:
            print(f"ReportManager: Error saving report JSON: {e}")
        
        # Generate HTML Report
        self._generate_html_report()

    def _generate_html_report(self):
        """Generates a standalone index.html file for the session."""
        if not self.current_report_dir:
            return

        html_path = os.path.join(self.current_report_dir, "index.html")
        
        steps_html = ""
        for step in self.report_data["steps"]:
            img_tag = ""
            if step.get("screenshot"):
                img_tag = f'<img src="{step["screenshot"]}" class="screenshot" onclick="window.open(this.src, \'_blank\')">'
            
            steps_html += f"""
            <div class="step">
                <div class="step-header">
                    <span class="step-idx">Step {step["step_index"]}</span>
                    <span class="step-time">{step["timestamp"]}</span>
                </div>
                <div class="step-content">
                    <div class="step-info">
                        <div class="thought"><strong>Thought:</strong> {step.get("thought")}</div>
                        <div class="plan"><strong>Plan:</strong> {step.get("plan")}</div>
                        <div class="action"><strong>Action:</strong> {json.dumps(step.get("action"))}</div>
                    </div>
                    {img_tag}
                </div>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Report: {self.report_data.get("goal")}</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                h1 {{ color: #38bdf8; }}
                .meta {{ background: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                .step {{ background: #1e293b; border: 1px solid #334155; margin-bottom: 20px; border-radius: 8px; overflow: hidden; }}
                .step-header {{ background: #334155; padding: 10px 15px; display: flex; justify-content: space-between; }}
                .step-content {{ padding: 15px; display: flex; gap: 20px; }}
                .step-info {{ flex: 1; }}
                .screenshot {{ width: 300px; height: auto; border-radius: 4px; cursor: pointer; border: 1px solid #475569; }}
                .thought, .plan, .action {{ margin-bottom: 10px; padding: 8px; background: #0f172a; border-radius: 4px; }}
                strong {{ color: #94a3b8; display: block; font-size: 0.8em; margin-bottom: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Execution Report</h1>
                <div class="meta">
                    <div><strong>Goal:</strong> {self.report_data.get("goal")}</div>
                    <div><strong>Status:</strong> {self.report_data.get("status")}</div>
                    <div><strong>Start Time:</strong> {self.report_data.get("start_time")}</div>
                    <div><strong>End Time:</strong> {self.report_data.get("end_time", "N/A")}</div>
                </div>
                <div class="steps">
                    {steps_html}
                </div>
            </div>
        </body>
        </html>
        """
        
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            print(f"ReportManager: Error saving report HTML: {e}")

    def get_all_reports(self):
        """Scans the reports directory and returns a list of summaries."""
        reports = []
        if not os.path.exists(self.base_dir):
            return reports

        # List all subdirectories
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            if os.path.isdir(item_path):
                # Try to read report.json
                json_path = os.path.join(item_path, "report.json")
                if os.path.exists(json_path):
                    try:
                        with open(json_path, "r") as f:
                            data = json.load(f)
                            # Append summary info
                            reports.append({
                                "id": item, # Directory name as ID
                                "timestamp": data.get("start_time"),
                                "goal": data.get("goal"),
                                "status": data.get("status"),
                                "step_count": len(data.get("steps", []))
                            })
                    except:
                        pass
        
        # Sort by timestamp, newest first
        return sorted(reports, key=lambda x: x.get("timestamp", ""), reverse=True)
