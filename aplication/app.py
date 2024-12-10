from fastapi import FastAPI, Form, File, UploadFile, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from psycopg2.errors import UniqueViolation
from jinja2 import Environment, FileSystemLoader
import redis.asyncio as redis
import os
import schedule_worker

DATABASE_URL = "postgresql://main_data:password@kursach_postgre/main_data_db"  # Замените на ваши данные
engine = create_engine(DATABASE_URL, echo=True)
sm = sessionmaker(bind=engine)

UPLOAD_DIR_AVATARS = "avatars"
UPLOAD_DIR_JSON = "users_jsons"
os.makedirs(UPLOAD_DIR_AVATARS, exist_ok=True)
os.makedirs(UPLOAD_DIR_JSON, exist_ok=True)
templates = Jinja2Templates(directory="sites")

redis_client = redis.from_url("redis://redis:6379")

app = FastAPI()
app.mount("/avatars", StaticFiles(directory="avatars"),name="avatars")
app.mount("/users_html", StaticFiles(directory="users_html"),name="users_html")

@app.get("/")
async def login_page(request : Request):
    if request.cookies.get("session_key_value"):
        return templates.TemplateResponse("main.html", {"request": request})
    return templates.TemplateResponse("login.html", {"request": request, "error_message": ""})

@app.get("/register")
async def register_page():
    return FileResponse("sites/regin.html")

@app.post("/login", response_class = FileResponse)
async def loginlogin(response: Response, request : Request,username: str = Form(...), password: str = Form(...)):
    try:
        with sm() as session:
            query = text("SELECT * FROM \"USER\" WHERE username = :username AND password = :password")
            result = session.execute(query, {"username": username, "password": password}).fetchone()
            if result:
                response = RedirectResponse(url="http://192.168.1.106:8000/main", status_code=301)
                response.set_cookie(key="session_key_value", value=f"{result[0]}")
                redis_client.set(f"session_key_value:{result[0]}",result[0])
                return response
            else:
                return templates.TemplateResponse("login.html", {"request": request, "error_message": "Неверное имя пользователя или пароль"})
    except SQLAlchemyError as e:
        return {"error" : str(e)}
    #return {"username": username, "password": password}

@app.post("/register")
async def loginlogin(request : Request, username: str = Form(...), password: str = Form(...), avatar : UploadFile = File(...)):
    filename = avatar.filename
    path_to_file = os.path.join(UPLOAD_DIR_AVATARS, filename)
    with open(path_to_file, "wb") as buffer:
        buffer.write(await avatar.read())
    try:
        with sm() as session:
            query = text("SELECT * FROM \"USER\" WHERE username = :username")
            result = session.execute(query, {"username": username, "password": password}).fetchone()
            if result:
                return templates.TemplateResponse("login.html", {"request": request, "error_message": "Пользователь с таким именем уже существует"})
            query = text("INSERT INTO \"USER\" (username, password, path_to_file) VALUES (:username, :password, :avatar_path)")
            session.execute(query, {"username": username, "password": password, "avatar_path": path_to_file})
            session.commit()
    except SQLAlchemyError as error:
        return {"error" : str(error)}
    return FileResponse("sites/successful_login.html")

@app.post("/exit")
async def exit_login(req : Request, response : Response):
    response = FileResponse("sites/exit_login.html")
    response.delete_cookie(key="session_key_value")
    return response

@app.get("/main")
async def main(request: Request, response: Response):
    return await get_session_info(request)

@app.post("/upload_json")
async def upload_json(req: Request, new_json : UploadFile):
    id = req.cookies.get("session_key_value")
    files = os.listdir("users_jsons")
    print(files)
    counter = 0
    for file in files:
        if f"{id}_" in file:
            counter += 1
    filename = f"{id}_{counter}_{new_json.filename}"
    path_to_file = os.path.join(UPLOAD_DIR_JSON, filename)
    with open(path_to_file, "wb") as buffer:
        buffer.write(await new_json.read())
    try:
        with sm() as session:
            query = text("INSERT INTO \"SCHEDULE\" (file_path_to_schedule) VALUES (:file_path_to_schedule)")
            session.execute(query, {"file_path_to_schedule": path_to_file})
            session.commit()
            query = text("SELECT schedule_id FROM \"SCHEDULE\" WHERE file_path_to_schedule = :file_path_to_schedule")
            result = session.execute(query, {"file_path_to_schedule": path_to_file}).fetchall()
            shedule_id = int(result[0][0]) 
            query = text("SELECT * FROM \"USER_LIST\" WHERE user_user_id = :user_user_id")
            result = session.execute(query, {"user_user_id" : id}).fetchall()
            query = text("INSERT INTO \"USER_LIST\" (user_user_id, schedule_id) VALUES (:user_user_id, :shedule_id)")
            session.execute(query, {"user_user_id": id, "shedule_id" : shedule_id})
            session.commit()
            #if not await get_schedule_via_json(result[0][1]): get_session_info(req, "Не удалось создать расписание. Не достоачно преподавателей, кабинетов или времени.")
            return await get_session_info(req)#RedirectResponse(url="http://localhost:8000/main", status_code=201)
    except SQLAlchemyError as error:
        if isinstance(error.orig, UniqueViolation):
            print("Не критичная ошибка добавления")
            print(result)
            get_schedule_via_json(result[0][1])
            return await get_session_info(req)#RedirectResponse(url="http://localhost:8000/main", status_code=302)
        return {"error" : str(error)}

@app.post("/use_loaded_json")
async def use_users_loaded_json(req : Request):
    cookie = req.cookies.get("session_key_value")
    with sm() as session:
        query = text("SELECT * FROM \"USER_LIST\" WHERE user_user_id = :user_user_id")
        result = session.execute(query, {"user_user_id" : cookie}).fetchall()
        schedule_file_id = result[-1][1]
        print(schedule_file_id)
        query = text("SELECT * FROM \"SCHEDULE\" WHERE schedule_id = :schedule_id")
        path_to_file = session.execute(query, {"schedule_id": schedule_file_id}).fetchall()[0][1]
        await get_schedule_via_json(path_to_file)
        schedule = schedule_worker.generate_schedule(path_to_file)
        schedule = schedule_worker.sort_schedule_by_time(schedule)
        if not schedule:
            print("Невозможно составить расписание")
            return await get_session_info(req, msg="Невозможно составить расписание, не хватает преподавателей, комант или времени")
        env = Environment(loader=FileSystemLoader("./sites/"))
        template = env.get_template('schedule_template.html')
        output_html = template.render(schedule=schedule)
        with open(f"users_html/{schedule_file_id}_schedule.html", "w", encoding="utf-8") as f:
            f.write(output_html)
        return RedirectResponse(url="http://192.168.1.106:8000/main", status_code=302) 

@app.get("/show_json")
async def show_current_json(req : Request):
    cookie = req.cookies.get("session_key_value")
    with sm() as session:
        query = text("SELECT * FROM \"USER_LIST\" WHERE user_user_id = :user_user_id")
        result = session.execute(query, {"user_user_id" : cookie}).fetchall()
        query = text("SELECT * FROM \"SCHEDULE\" WHERE schedule_id = :schedule_id")
        path_to_file = session.execute(query, {"schedule_id": result[-1][1]}).fetchall()[0][1]
        print(path_to_file)
        if os.path.exists(path_to_file):
            return FileResponse(path_to_file)
        return await get_session_info(req, msg="Файл не существует")

@app.get("/editor")
async def json_editor():
    return FileResponse("sites/editor.html")

@app.get("/delete_schedule")
async def delete_schedule(req : Request, delete_schedule : str):
    os.remove(f"users_html/{delete_schedule}")
    id = delete_schedule.split('_')[0]
    with sm() as session:
        query = text("DELETE FROM \"SCHEDULE\" WHERE schedule_id = :schedule_id")
        session.execute(query, {"schedule_id" : id})
        query = text("DELETE FROM \"USER_LIST\" WHERE schedule_id = :schedule_id")
        session.execute(query, {"schedule_id" : id})
    return await get_session_info(req)

async def get_schedule_via_json(path_to_file):
    schedule = schedule_worker.generate_schedule(path_to_file)
    if not schedule:
        print("Невозможно составить расписание")
        return False
    print("Расписание университета:")
    for entry in schedule:
        print(
            f"{entry['group_name']} - {entry['time_slot']}: {entry['course_name']} "
            f"(Преподаватель: {entry['teacher_name']}, Аудитория: {entry['room_name']})"
            )

async def get_ready_schedules_by_user(shedule_id):
    files = os.listdir("users_html")
    name_shedule = f"{shedule_id}_schedule.html"
    if name_shedule in files:
        with sm() as session:
            query = text("SELECT * FROM \"SCHEDULE\" WHERE schedule_id = :schedule_id")
            result = session.execute(query, {"schedule_id" : shedule_id}).fetchall()
            json_name = str(result[0][1]).split("jsons/")[1]
        return (json_name,name_shedule)
    
async def get_session_info(req: Request, msg : str = ""):
    with sm() as session:
            schedules = []
            shedules_list = []
            query = text("SELECT * FROM \"USER\" WHERE user_id = :user_id")
            query_shedule_id = text("SELECT * FROM \"USER_LIST\" WHERE user_user_id = :user_id")
            user_id = req.cookies.get("session_key_value")
            result = session.execute(query, {"user_id": user_id}).fetchone()
            result_shedule_id = session.execute(query_shedule_id,{"user_id": user_id}).fetchall()
            for sch_num in result_shedule_id:
                if sch_num[1] not in schedules:
                    schedules.append(sch_num[1])
            for s in schedules:
                answer = await get_ready_schedules_by_user(s)
                if answer != None:
                    shedules_list.append(await get_ready_schedules_by_user(s))
            print(shedules_list)
            username = result[1]
            avatar_path = result[3]
            return templates.TemplateResponse("main.html",{
            "request": req,
            "shedules_list" : shedules_list,
            "avatar_path": f"{avatar_path}",
            "username" : f"{username}",
            "error_message": f"{msg}"
        })