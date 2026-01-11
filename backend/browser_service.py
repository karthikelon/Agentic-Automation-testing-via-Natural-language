import asyncio
import base64
from playwright.async_api import async_playwright, Page, Browser

class BrowserService:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Page = None
        self.playwright_context = None
        self.cdp_session = None
        self.console_logs = []
        self.network_errors = []

    async def start(self):
        """Starts the browser."""
        self.playwright = await async_playwright().start()
        # Launching headed so the user can see it (Visual Truth)
        # In a real deployed version, this might be headless with streaming, 
        # but for MVP running locally, headed is best.
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        # Set a reasonable viewport
        await self.page.set_viewport_size({"width": 1280, "height": 720})
        
        # Initialize CDP Session
        self.cdp_session = await self.context.new_cdp_session(self.page)
        await self.cdp_session.send("Runtime.enable")
        await self.cdp_session.send("Log.enable")
        await self.cdp_session.send("Accessibility.enable")
        
        # Setup event listeners
        self.page.on("console", lambda msg: self.console_logs.append(f"[{msg.type}] {msg.text}"))
        self.page.on("pageerror", lambda exc: self.network_errors.append(f"Page Error: {exc}"))
        self.page.on("requestfailed", lambda req: self.network_errors.append(f"Request Failed: {req.url} ({req.failure})"))

    async def stop(self):
        """Stops the browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def go_to_url(self, url: str):
        """Navigates to a URL."""
        if not self.page:
            await self.start()
        await self.page.goto(url)
        await self.page.wait_for_load_state("domcontentloaded")

    async def get_screenshot_base64(self) -> str:
        """Takes a screenshot and returns it as a base64 string."""
        if not self.page:
            return None
        screenshot_bytes = await self.page.screenshot(type='jpeg', quality=50) # Low quality for speed/AI
        return base64.b64encode(screenshot_bytes).decode('utf-8')

    async def get_page_content(self) -> str:
        """Returns the current page content (simplified if needed)."""
        if not self.page:
            return ""
        # Maybe strip scripts/styles to save tokens? 
        # For now, just raw HTML or text might be fine, but screenshot is primary for Multimodal.
        # Let's return the body text for accessibility context.
        return await self.page.evaluate("document.body.innerText")

    async def execute_action(self, action_type: str, selector: str = None, value: str = None, node_id: str = None):
        """Executes a specific action on the page."""
        if not self.page:
            raise Exception("Browser not started")

        # 1. NEW: CDP-First Interaction (using node_id if provided)
        if node_id and action_type in ["click", "type", "hover"]:
            print(f"BrowserService: Protocol Interaction for {action_type} on Node {node_id}")
            try:
                # Resolve the AX Node to its backend DOM ID
                ax_tree = await self.get_accessibility_snapshot()
                target_node = next((n for n in ax_tree.get("nodes", []) if n.get("nodeId") == node_id), None)
                
                if target_node and "backendDOMNodeId" in target_node:
                    backend_id = target_node["backendDOMNodeId"]
                    # Use CDP to find coordinates
                    box = await self.cdp_session.send("DOM.getBoxModel", {"backendNodeId": backend_id})
                    if box and "model" in box:
                        quad = box["model"]["content"]
                        # Quad is [x1, y1, x2, y2, x3, y3, x4, y4]
                        x = (quad[0] + quad[2] + quad[4] + quad[6]) / 4
                        y = (quad[1] + quad[3] + quad[5] + quad[7]) / 4
                        
                        # Use Playwright's mouse/keyboard for better event handling on top of coordinates
                        if action_type == "click":
                            await self.page.mouse.click(x, y)
                        elif action_type == "type":
                            await self.page.mouse.click(x, y) # Focus first
                            await self.page.keyboard.type(value)
                        elif action_type == "hover":
                            await self.page.mouse.move(x, y)
                        
                        await self.page.wait_for_load_state("networkidle", timeout=5000)
                        return
                    else:
                        print(f"BrowserService: Could not get BoxModel for node {node_id}")
                else:
                    print(f"BrowserService: Node {node_id} not found or has no backend ID")
            except Exception as e:
                print(f"BrowserService: CDP Fallback failed: {e}")
                # Fall back to selector if provided

        # 2. Selector-based Fallback (Legacy)
        if selector:
            try:
                await self.page.evaluate(f"""
                    (sel) => {{
                        const el = document.querySelector(sel);
                        if (el) {{
                            el.style.outline = '4px solid #6d28d9';
                            el.style.outlineOffset = '2px';
                            setTimeout(() => {{ el.style.outline = ''; }}, 2000);
                        }}
                    }}
                """, selector)
                await asyncio.sleep(0.3)
            except:
                pass

        if action_type == "navigate":
            url = value or selector
            if not url.startswith("http"):
                url = f"https://{url}"
            print(f"BrowserService: Navigating to {url}...")
            try:
                await self.page.goto(url, timeout=30000)
                await self.page.wait_for_load_state("load", timeout=10000)
            except Exception as e:
                print(f"BrowserService: Navigation Warning: {e}")

        elif action_type == "click":
            await self.page.click(selector)
        elif action_type == "type":
            await self.page.fill(selector, value)
        elif action_type == "press":
            await self.page.keyboard.press(value)
        elif action_type == "hover":
            await self.page.hover(selector)
        elif action_type == "scroll":
            if selector:
                await self.page.locator(selector).scroll_into_view_if_needed()
            else:
                await self.page.evaluate("window.scrollBy(0, 500)")
        
        await self.page.wait_for_load_state("networkidle", timeout=5000)

    async def get_accessibility_snapshot(self):
        """Fetches and simplifies AXTree to minimize tokens and focus on interactive nodes."""
        if not self.cdp_session:
            return {"nodes": []}
        
        try:
            raw_tree = await self.cdp_session.send("Accessibility.getFullAXTree")
            nodes = raw_tree.get("nodes", [])
            
            # Simple heuristic: only keep nodes with names OR roles like 'button', 'link', 'textbox'
            # To save tokens while keeping the "Protocol" advantage.
            simplified = []
            interactive_roles = ["button", "link", "textbox", "checkbox", "combobox", "listbox", "searchbox", "menuitem"]
            
            for n in nodes:
                # We want nodes that have a name or are in interactive roles
                role = n.get("role", {}).get("value")
                name = n.get("name", {}).get("value")
                if (role in interactive_roles) or (name and len(name) > 1):
                    simplified.append({
                        "nodeId": n.get("nodeId"),
                        "role": role,
                        "name": name,
                        "backendDOMNodeId": n.get("backendDOMNodeId")
                    })
            return {"nodes": simplified}
        except Exception as e:
            print(f"Error fetching/simplifying AXTree: {e}")
            return {"nodes": []}

    def get_and_clear_events(self):
        """Returns collected logs/errors and clears the buffers."""
        events = {
            "console": self.console_logs.copy(),
            "errors": self.network_errors.copy()
        }
        self.console_logs.clear()
        self.network_errors.clear()
        return events
