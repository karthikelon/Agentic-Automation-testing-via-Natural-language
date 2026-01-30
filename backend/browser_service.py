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

    async def highlight_element(self, selector: str):
        """Highlights an element using Playwright locator."""
        if not self.page or not selector:
            return
        try:
            # Create a locator
            locator = self.page.locator(selector).first
            # Scroll into view if needed
            await locator.scroll_into_view_if_needed()
            # Apply Red Box
            await locator.evaluate("""
                (el) => {
                    const originalOutline = el.style.outline;
                    const originalOffset = el.style.outlineOffset;
                    el.style.outline = '3px solid #ef4444'; // Tailwind Red-500
                    el.style.outlineOffset = '2px';
                    // Reset after 1s
                    setTimeout(() => {
                        el.style.outline = originalOutline;
                        el.style.outlineOffset = originalOffset;
                    }, 1500);
                }
            """)
            # Brief pause for human observer
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"BrowserService: Highlight failed for {selector}: {e}")

    async def execute_action(self, action_type: str, selector: str = None, value: str = None, node_id: str = None):
        """Executes a specific action on the page."""
        if not self.page:
            raise Exception("Browser not started")

    async def execute_action(self, action_type: str, selector: str = None, value: str = None, node_id: str = None):
        """Executes a specific action on the page using Hybrid SOTA Strategy."""
        if not self.page:
            raise Exception("Browser not started")

        print(f"BrowserService: Executing {action_type} (NodeID: {node_id}, Selector: {selector})")

        # 1. PRIMARY: CDP/Protocol Interaction (Human-like Physics)
        if node_id and action_type in ["click", "type", "hover"]:
            print(f"BrowserService: Protocol Interaction (Primary) for {action_type} on Node {node_id}")
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
                        # Calculate Center
                        x = (quad[0] + quad[2] + quad[4] + quad[6]) / 4
                        y = (quad[1] + quad[3] + quad[5] + quad[7]) / 4
                        
                        # Apply Human-like Physics (Move -> Hover -> Act)
                        
                        # 1. Visual Feedback (Red Dot)
                        await self.page.evaluate(f"""
                            const dot = document.createElement('div');
                            dot.style.position = 'absolute';
                            dot.style.left = '{x}px';
                            dot.style.top = '{y}px';
                            dot.style.width = '10px';
                            dot.style.height = '10px';
                            dot.style.background = 'red';
                            dot.style.borderRadius = '50%';
                            dot.style.zIndex = '99999';
                            dot.style.pointerEvents = 'none'; // Don't block click
                            document.body.appendChild(dot);
                            setTimeout(() => dot.remove(), 1000);
                        """)
                        
                        # 2. Physics: Move Mouse
                        await self.page.mouse.move(x, y, steps=5) # Steps adds "human" drag latency
                        await asyncio.sleep(0.1) 
                        
                        if action_type == "click":
                            await self.page.mouse.click(x, y)
                        elif action_type == "type":
                            await self.page.mouse.click(x, y)
                            await self.page.keyboard.type(value)
                        
                        await self.page.wait_for_load_state("networkidle", timeout=5000)
                        return # Success!
                    else:
                        print(f"BrowserService: Could not get BoxModel for node {node_id}")
            except Exception as e:
                print(f"BrowserService: CDP Fallback failed: {e}")
                # Continue to Locator Fallback...

        # 2. SECONDARY: Locator-Based Interaction (Fallback)
        if selector and action_type in ["click", "type", "hover", "scroll"]:
            print(f"BrowserService: Locator Fallback for {action_type} on {selector}")
            try:
                # Highlight first
                await self.highlight_element(selector)
                
                locator = self.page.locator(selector).first
                
                if action_type == "click":
                    await locator.click(timeout=5000)
                elif action_type == "type":
                    await locator.fill(value, timeout=5000)
                elif action_type == "hover":
                    await locator.hover(timeout=5000)
                elif action_type == "scroll":
                    await locator.scroll_into_view_if_needed(timeout=5000)
                
                await self.page.wait_for_load_state("networkidle", timeout=5000)
                return
            except Exception as e:
                print(f"BrowserService: Locator action failed ({e}).")

        # 3. Simple Fallbacks
        if action_type == "navigate":
            url = value or selector
            if url:
                if not url.startswith("http"):
                    url = f"https://{url}"
                print(f"BrowserService: Navigating to {url}...")
                await self.page.goto(url, timeout=30000)
                await self.page.wait_for_load_state("load", timeout=10000)

        elif action_type == "press":
            await self.page.keyboard.press(value)
        elif action_type == "scroll" and not selector:
             await self.page.evaluate("window.scrollBy(0, 500)")
        
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            print("BrowserService: Network didn't idle in 5s (proceeding anyway)")

    async def get_accessibility_snapshot(self):
        """Fetches 'Active' AXTree: Visible & Interactive nodes only (Token Efficient)."""
        if not self.cdp_session:
            return {"nodes": []}
        
        try:
            # 1. Fetch Full Tree
            raw_tree = await self.cdp_session.send("Accessibility.getFullAXTree")
            nodes = raw_tree.get("nodes", [])
            
            # 2. Heuristic Filter (Active Accessibility)
            simplified = []
            interactive_roles = ["button", "link", "textbox", "checkbox", "combobox", "listbox", "searchbox", "menuitem", "menu", "tab"]
            
            for n in nodes:
                role = n.get("role", {}).get("value")
                name = n.get("name", {}).get("value") or ""
                
                # SOTA Filter: Must have a Role AND (be interactive OR have a Name)
                # This removes structural <div> soup that has no semantic meaning.
                is_interactive = role in interactive_roles
                has_content = len(name) > 0
                
                if (is_interactive) or (role == "statictext" and len(name) > 3) or (role == "image" and has_content):
                    # Exclude obviously ignored nodes if property exists (CDP specific)
                    if n.get("ignored"): 
                        continue

                    simplified.append({
                        "nodeId": n.get("nodeId"),
                        "role": role,
                        "name": name[:100], # Trucate long text
                        "backendDOMNodeId": n.get("backendDOMNodeId")
                    })
            
            # Limit to top 200 nodes to prevent context window explosion
            return {"nodes": simplified[:200]}
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
