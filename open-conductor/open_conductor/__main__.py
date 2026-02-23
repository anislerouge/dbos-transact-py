"""Entry point: python -m open_conductor"""

import uvicorn
from open_conductor.config import OpenConductorConfig


def main() -> None:
    config = OpenConductorConfig()
    uvicorn.run(
        "open_conductor.server.app:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        reload=True,
    )


if __name__ == "__main__":
    main()
