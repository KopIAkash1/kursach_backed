import json
from datetime import datetime

courses = []
teachers = []
rooms = []
time_slots = []
groups = []

def get_data_from_json(json_name : str):
    global courses, teachers, rooms, time_slots, groups
    with open(f"{json_name}", "rb") as file:
        data = json.load(file)
    courses = data['courses']
    teachers = data['teachers']
    rooms = data['rooms']
    time_slots = data['time_slots']
    groups = data['groups']
    return True

def is_teacher_available(schedule, teacher_id, time_slot):
    for entry in schedule:
        if entry["time_slot"] == time_slot and entry["teacher_id"] == teacher_id:
            return False
    return True

def is_room_available(schedule, room_id, time_slot):
    for entry in schedule:
        if entry["time_slot"] == time_slot and entry["room_id"] == room_id:
            return False
    return True

def generate_schedule(json_name : str):
    get_data_from_json(f"/var/www/html/{json_name}")
    schedule = []
    for group in groups:
        for course in courses:
            assigned = False

            for teacher in teachers:#teacher in teachers:
                if assigned:
                    break
                for room in rooms:#room in rooms:
                    if assigned:
                        break
                    for time_slot in time_slots:
                        # Проверяем доступность преподавателя и аудитории
                        if (
                            is_teacher_available(schedule, teacher["teacher_id"], time_slot)
                            and is_room_available(schedule, room["room_id"], time_slot)
                        ):
                            schedule.append({
                                "group_id": group["group_id"],
                                "group_name": group["name"],
                                "course_id": course["course_id"],
                                "course_name": course["name"],
                                "teacher_id": teacher["teacher_id"],
                                "teacher_name": teacher["name"],
                                "room_id": room["room_id"],
                                "room_name": room["name"],
                                "time_slot": time_slot,
                            })
                            assigned = True
                            break

            if not assigned:
                print(
                    f"Не удалось назначить {course['name']} для {group['name']}. "
                    f"Недостаточно преподавателей, комнат или времени."
                )
                return False
    
    return schedule

def sort_schedule_by_time(schedule):
    def parse_time_slot(time_slot):
        start_time = time_slot.split('-')[0]
        return datetime.strptime(start_time, "%H:%M")
    
    return sorted(schedule, key=lambda x: parse_time_slot(x["time_slot"]))




if __name__ == "__main__":
    schedule = generate_schedule()
    print(schedule)
    if not schedule:
        exit(-1)
    #schedule = sort_schedule_by_time(schedule)
    print("Расписание университета:")
    if not schedule:
        for entry in schedule:
            print(
                f"{entry['group_name']} - {entry['time_slot']}: {entry['course_name']} "
                f"(Преподаватель: {entry['teacher_name']}, Аудитория: {entry['room_name']})"
            )