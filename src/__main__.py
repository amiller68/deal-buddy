import sys
import uvicorn
from typing import Optional

from src.state import AppState
from src.server import create_app
from src.config import Config

def init_state(config: Config) -> Optional[AppState]:
    """Initialize application state"""
    try:
        state = AppState.from_config(config)
        print("✓ Application state initialized")
        return state
    except Exception as e:
        print(f"✗ Failed to initialize application state: {e}")
        return None

# Initialize at module level
config = Config()
config.show()
state = init_state(config)
app = create_app(state) if state else None

def main() -> int:
    """Main entrypoint for the server"""
    try:
        if not state or not app:
            print("✗ Failed to initialize application")
            return 1
        
        print(f"✓ Configuration loaded from environment")
        
        print("✓ FastAPI application created")
        
        # Start server
        print(f"Starting server on {config.listen_address}:{config.listen_port}")
        uvicorn.run(
            "src.__main__:app",
            host=config.listen_address,
            port=config.listen_port,
            proxy_headers=True,
            reload=config.dev_mode,
            reload_dirs=["src"]
        )
        return 0
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
