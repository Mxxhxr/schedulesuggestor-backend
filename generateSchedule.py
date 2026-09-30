from datetime import datetime
from itertools import product
from collections import defaultdict

# filter out combos with time conflicts, and violations of time preferences
# return clean JSON with each valid schedule


def time_str_to_minutes(t):
    # convert time string into minutes since midnight
    # ex. "2:30 PM" becomes 14 * 60 + 30 = 870
    # ex. "11:00 AM" becomes 11 * 60 + 0 = 660
    dt = datetime.strptime(t.strip(), "%I:%M %p")
    return dt.hour * 60 + dt.minute

def get_sections_for_courses(course_list, mysql):
    # get sections for each course in course_list
    if not course_list:
        return {}

    cur = mysql.connection.cursor()

    # format for SQL IN clause
    format_str = ','.join(['%s'] * len(course_list))

    # step 1: fetch sections
    cur.execute(f"""
        SELECT
            cs.id as section_id,
            cs.course_code,
            cs.section,
            cs.mode,
            cs.title,
            cs.credits,
            cs.instructor,
            sm.day_of_week,
            TIME_FORMAT(sm.start_time, '%%l:%%i %%p') as start,
            TIME_FORMAT(sm.end_time, '%%l:%%i %%p') as end
        FROM CourseSections cs
        JOIN SectionMeetings sm ON cs.id = sm.section_id
        WHERE cs.course_code IN ({format_str})
        ORDER BY cs.course_code, cs.section, sm.day_of_week
    """, course_list)

    results = cur.fetchall()

    # step 2: organize results by course_code
    section_map = defaultdict(list)
    seen_sections = {}

    for row in results:
        key = (row['course_code'], row['section'])

        if key not in seen_sections:
            seen_sections[key] = {
                "section": row['section'],
                "mode": row['mode'],
                "title": row['title'],
                "credits": row['credits'],
                "instructor": row['instructor'],
                "meetings": []
            }

        seen_sections[key]["meetings"].append({
            "day": row['day_of_week'],
            "start": row['start'],
            "end": row['end']
        })

    # step 3: convert seen_sections to final structure
    for (course_code, _), section in seen_sections.items():
        section_map[course_code].append(section)

    return section_map

def is_within_preference(section, prefs):
    meetings = section.get("meetings", [section])  # fallback to flat sections
    for m in meetings:
        day = m["day"]
        if day not in prefs:
            return False
        start = time_str_to_minutes(m["start"])
        end = time_str_to_minutes(m["end"])
        pref_start = 420 if prefs[day]["start"] == "All Day" else time_str_to_minutes(prefs[day]["start"])
        pref_end = 1320 if prefs[day]["end"] == "All Day" else time_str_to_minutes(prefs[day]["end"])
        if start < pref_start or end > pref_end:
            return False
    return True

def has_time_conflict(sections):
    schedule = []
    for section in sections:
        meetings = section.get("meetings", [section])  # fallback to flat sections
        for m in meetings:
            day = m["day"]
            start = time_str_to_minutes(m["start"])
            end = time_str_to_minutes(m["end"])
            for existing in schedule:
                if existing["day"] == day and not (end <= existing["start"] or start >= existing["end"]):
                    return True
            schedule.append({"day": day, "start": start, "end": end})
    return False

def generate_schedule(selected_courses, time_preferences, mysql=None):
    if not mysql:
        raise ValueError("Database connection is required in production")

    course_sections = get_sections_for_courses(selected_courses, mysql)

    # A course with zero sections (e.g. fully-async online, or not found in
    # the DB) makes every combination impossible before we even get to
    # conflict/preference checking. Surface that explicitly instead of just
    # returning an empty schedules list with no explanation.
    unavailable_courses = [c for c in selected_courses if not course_sections.get(c)]
    if unavailable_courses:
        return {
            "schedules": [],
            "unavailable_courses": unavailable_courses
        }

    sections_options = [course_sections.get(course, []) for course in selected_courses]
    all_combos = product(*sections_options)

    valid_schedules = []
    for combo in all_combos:
        if has_time_conflict(combo):
            continue
        if all(is_within_preference(section, time_preferences) for section in combo):
            schedule = {selected_courses[i]: combo[i] for i in range(len(selected_courses))}
            valid_schedules.append(schedule)
    return {"schedules": valid_schedules}