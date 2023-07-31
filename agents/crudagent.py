from elevenlabs import generate, save
import requests
import json
import os
from fastapi import FastAPI, Form, File, UploadFile
from bson import ObjectId
from fastapi import APIRouter, Request
from pymongo import MongoClient
import asyncio
from agents.knowledgeAgent import knowledgeTalk
from agents.landingpageAgent import invoke_landingpage_agent
router = APIRouter()
client = MongoClient("mongodb://localhost:27017/")
db = client["aisplain"]
UPLOAD_FOLDER = "uploads"
from elevenlabs import set_api_key
import whisper
from nanoid import generate as generate_id
model = whisper.load_model("small", "cpu")
@router.get("/crud-agent")
def crudAgent_endpoint():
    return {"message": "Hello from Crud Agent, Okay I'm not really an agent"}


@router.post("/create-project")
async def create_project(request: Request):
    data = await request.json()
    print(data)
    new_project = db.projects.insert_one(data)
    print(new_project.inserted_id)
    projectid = str(new_project.inserted_id)
    asyncio.create_task(invoke_landingpage_agent(
        projectid, data["url"], data["tone"]))
    return {"message": "Project created", "project_id": str(new_project.inserted_id)}


@router.get("/get-project/{project_id}")
async def get_project(project_id: str):
    project = db.projects.find_one({"_id": ObjectId(project_id)})
    project["_id"] = str(project["_id"])
    return {"message": "successful", "project": project}


@router.get("/get-all")
async def get_all_projects():
    projects = db.projects.find({})
    final = []
    for project in projects:
        project["_id"] = str(project["_id"])
        final.append(project)
    return {"message": "successful", "projects": final}


@router.post("/talk-to-agent")
async def upload_file(apiKey: str = Form(...), file: UploadFile = File(...)):
    # Process the apiKey field
    print("API Key:", apiKey)

    # Create the uploads folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        os.makedirs("quickaudio")

    # Save the uploaded file to the uploads folder with a custom filename
    file_name = os.path.join(UPLOAD_FOLDER, f"uploaded_{file.filename}")
    with open(file_name, "wb") as f:
        f.write(await file.read())


    stoc = model.transcribe(file_name)
    print(stoc["text"])
    project = db.projects.find_one({"_id": ObjectId(apiKey)})
    print(project)
    urls = project["docsUrl"]
    print(type(urls))
    answer = knowledgeTalk(stoc["text"], urls)
    set_api_key("add your key here")
    audio = generate(
        text= answer,
        voice="Valley",
        model="eleven_monolingual_v1"
    )
    fname = generate_id()
    save(audio, "./quickaudio/"+fname+".mp3")
    return {"message": "successful", "response": answer, "audio": fname+".mp3"}


@router.get("/landingpage-talk/{project_id}")
async def landingPage_talk(project_id: str):
    project = db.projects.find_one({"_id": ObjectId(project_id)})
    return {"message": "successful", "response": project["landingPageContent"]}
