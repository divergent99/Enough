import json, os, re
from openai import OpenAI
from .models import ReflectionRequest, ReflectionResponse

URGENT_PATTERNS=[r"\bkill myself\b",r"\bend my life\b",r"\bsuicid(?:e|al)\b",r"\bhurt myself\b",r"\bdo not want to live\b"]
SYSTEM="""You are the reflection engine inside Enough, a gentle wellbeing companion. You are not a therapist. Never diagnose, prescribe, recommend medication changes, claim treatment, or pretend to be human. Avoid toxic positivity and clichés. Respect grief and agency. Return JSON matching the schema. Acknowledge the specific experience calmly. Extract a concise feeling without diagnosis. Separate at most 3 controllable items from at most 2 things that can wait. Offer exactly one tiny next step proportional to the user's energy. If an agent is selected, let its quality subtly shape the delivery: sentinel=steady and protective, duelist=direct and activating, strategist=clear and analytical, healer=patient and compassionate, wanderer=reflective and philosophical. Never roleplay a copyrighted character. If there is explicit self-harm or suicide intent, set safety to urgent and direct the user toward immediate human help. Otherwise never treat ordinary sadness, panic, grief, or feeling low as an emergency."""

def is_urgent(text):
    return any(re.search(p,text.lower()) for p in URGENT_PATTERNS)

def demo_reflection(req):
    if is_urgent(req.text):
        return ReflectionResponse(acknowledgement="This sounds like a moment that needs a real person beside you, not something you should carry alone.",feeling="overwhelmed and unsafe",controllable=["Contact someone you trust now","Move toward a safer shared space"],can_wait=["Solving everything else"],next_step="Call local emergency services or a trusted person and tell them you need immediate support.",mode="safety",safety="urgent")
    options={
      "panic":("Your body is sounding an alarm, and you do not have to solve anything while it settles.","alarmed and overwhelmed","Put both feet on the floor and name three things you can see."),
      "overthinking":("There is a lot moving through your mind at once; we can hold just one piece of it.","mentally crowded","Write the one question that actually needs an answer today."),
      "grief":("Missing someone can arrive without warning, and this moment does not need to be rushed away.","grieving and tender","Write one small thing you remember about them today."),
      "stuck":("Low energy can make even ordinary tasks feel enormous.","drained and stuck","Take one sip of water, then decide whether anything else is possible."),
      "checkin":("Thank you for noticing where you are today without judging it.","reflective","Choose one kind thing that would make the next hour gentler.")}
    ack,feeling,step=options[req.moment]
    accents={"sentinel":"We can keep this steady and close.","duelist":"We only need the next move, not the whole path.","strategist":"We can separate the signal from the noise.","healer":"There is room for this without rushing it away.","wanderer":"We can meet this moment without forcing an answer."}
    if req.agent: ack=f"{accents[req.agent]} {ack}"
    return ReflectionResponse(acknowledgement=ack,feeling=feeling,controllable=["What you do in the next ten minutes","Whether you ask someone for company"],can_wait=["Understanding the whole situation","Being productive"],next_step=step,mode="demo")

def reflect(req: ReflectionRequest):
    if is_urgent(req.text) or not os.getenv("OPENAI_API_KEY"): return demo_reflection(req)
    response=OpenAI().responses.create(model=os.getenv("OPENAI_MODEL","gpt-5.6"),instructions=SYSTEM,input=json.dumps(req.model_dump()),text={"format":{"type":"json_schema","name":"enough_reflection","strict":True,"schema":ReflectionResponse.model_json_schema()}})
    result=ReflectionResponse.model_validate_json(response.output_text); result.mode=os.getenv("OPENAI_MODEL","gpt-5.6"); return result
