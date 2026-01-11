import asyncio
import sys
import uvicorn
import os

# 1. Force Policy EARLY
if sys.platform == 'win32':
    print("Applying WindowsProactorEventLoopPolicy...")
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 2. Import app AFTER policy is set
try:
    from main import app
except ImportError:
    # Handle case where we might be in the wrong dir (though bat handles this)
    sys.path.append(os.getcwd())
    from main import app

if __name__ == "__main__":
    print("Starting Backend (Single Process Mode)...")
    # 3. Run directly with factory 'asyncio' which respects the global policy
    # Disable reload to avoid subprocess complexity
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")
