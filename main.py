import asyncio
from robot import Robot
from utils.config import load_config
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

async def main():
    setup_logging()
    config = load_config()
    robot = Robot(config)

    try:
        await robot.initialize()
        await robot.main_loop()
    except KeyboardInterrupt:
        await robot.shutdown()
        logging.info("Shutting down robot...")
    except Exception as e:
        logging.getLogger('main').critical(f"Unhandled exception: {e}")
        await robot.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 