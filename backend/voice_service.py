import logging
from livekit import agents
from livekit.agents import WorkerOptions, cli, JobContext, AgentSession
from livekit.plugins.openai import LLM
from livekit.plugins.elevenlabs import TTS
from livekit.plugins.deepgram import STT
from livekit.plugins.silero import VAD
from livekit.agents.voice.room_io import RoomInputOptions
import os
from dotenv import load_dotenv
from backend.definitions.session_data import UserData
from backend.logic.agent_impl import Greeter, Reservation, Takeaway, Checkout
import urllib.parse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-service")

MENU = "Pizza: $10, Salad: $5, Ice Cream: $3, Coffee: $2"
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "").strip()

if not LIVEKIT_URL:
    LIVEKIT_URL = "ws://localhost:7880"

if not LIVEKIT_URL.startswith(("wss://", "ws://", "https://", "http://")):
    LIVEKIT_URL = f"wss://{LIVEKIT_URL}"

LIVEKIT_HOST = LIVEKIT_URL.replace("wss://", "").replace("ws://", "").replace("https://", "").replace("http://", "").strip()

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()
    
    logger.info(f"Room: {ctx.room}")
    logger.info(f"Room metadata: {ctx.room.metadata}")
    logger.info(f"Worker ID: {ctx.worker_id}")
    logger.info(f"Job ID: {ctx.job.id if ctx.job else 'None'}")
    
    try:
        userdata = UserData()
        userdata.agents.update({
            "greeter": Greeter(MENU),
            "reservation": Reservation(),
            "takeaway": Takeaway(MENU),
            "checkout": Checkout(MENU),
        })

        session = AgentSession[UserData](
            userdata=userdata,
            stt=STT(model="nova-3", language="multi"),
            llm=LLM(model="gpt-4o-mini", timeout=30),
            tts=TTS(api_key=os.getenv("ELEVEN_API_KEY")),
            vad=VAD.load(),
        )

        logger.info("Agent running and waiting for participants...")
        await session.start(
            room=ctx.room,
            agent=userdata.agents["greeter"],
            room_input_options=RoomInputOptions(),
        )
        logger.info("Agent session started successfully")
        
        return session
    except Exception as e:
        logger.error(f"Error in agent session: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    options = agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    cli.run_app(options) 