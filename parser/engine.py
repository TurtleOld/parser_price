import asyncio
import threading
from parser.bot.messages import scheduler, start_bot


def main():
    thread = threading.Thread(target=scheduler)
    thread.start()
    asyncio.run(start_bot())


if __name__ == '__main__':
    main()
