import asyncio
from spin_bot.titan_stealth import TitanStealthClient

async def run_titan_cycle():
    print("--- OMNI MACHINE: PROJECT TITAN-STEALTH ---")
    client = TitanStealthClient()
    try:
        success = await client.login()
        if success:
            print("STATUS: Titan-Stealth Session Active. Ready for betting operations.")
            # Placeholder for future betting logic
            # await client.navigate_to_game()
            # ...
        else:
            print("STATUS: Titan-Stealth Auth Failed. Terminating Cycle.")
    finally:
        await client.close()
        print("--- TITAN-STEALTH CYCLE COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_titan_cycle())
