from datetime import datetime

def to_mysql_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").strftime("%H:%M:%S")
    except ValueError:
        print(f"[WARN] Could not parse time: '{time_str}'")
        return None

def load_courses_into_schedule_tables(mysql):
    cur = mysql.connection.cursor()

    # Clear out old data first so repeated runs (app restarts, /reload-data
    # calls, Flask's debug reloader running startup twice) don't pile up
    # duplicate SectionMeetings rows.
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("TRUNCATE TABLE SectionMeetings")
    cur.execute("TRUNCATE TABLE CourseSections")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    mysql.connection.commit()

    input_table = "RawCourseMeetings"

    cur.execute(f"""
        SELECT Course, Section, Title, DeliveryMode, Credits, Day, StartTime, EndTime, Instructor
        FROM `{input_table}`
    """)
    rows = cur.fetchall()
    section_map = {}

    for row in rows:
        key = (row['Course'], row['Section'])

        # Convert credits
        credits_raw = row['Credits']
        try:
            credits = float(credits_raw)
        except Exception:
            print(f"[SKIP] Invalid credits: '{credits_raw}' for {row['Course']} {row['Section']}")
            continue

        # Insert section if not seen
        if key not in section_map:
            # Check if already exists in DB
            cur.execute("""
                SELECT id FROM CourseSections
                WHERE course_code = %s AND section = %s
            """, (row['Course'], row['Section']))
            result = cur.fetchone()

            if result:
                section_id = result['id']
            else:
                cur.execute("""
                    INSERT INTO CourseSections (course_code, section, mode, title, credits, instructor)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (row['Course'], row['Section'], row['DeliveryMode'], row['Title'], credits, row['Instructor']))
                mysql.connection.commit()
                section_id = cur.lastrowid

            section_map[key] = section_id
        else:
            section_id = section_map[key]

        # Check if this row has valid meeting times
        start = row['StartTime']
        end = row['EndTime']
        day = row['Day']

        if start and end and day:
            cur.execute("""
                INSERT INTO SectionMeetings (section_id, day_of_week, start_time, end_time)
                VALUES (%s, %s, %s, %s)
            """, (section_id, day, start, end))
            mysql.connection.commit()

    print(f"Inserted {len(section_map)} unique sections with meetings.")

def retrieve_courses(course_name, mysql):
    cur = mysql.connection.cursor()
    table_names = ["CourseSections"]

    course_dict = {}

    for table_name in table_names:
        query = f"SELECT course_code AS Course, title AS Title, mode AS DeliveryMode, credits AS Credits FROM `{table_name}`"

        cur.execute(query)
        courses = cur.fetchall()

        for course in courses:
            course_key = course["Course"]
            if course_name is None or course_key.startswith(course_name.upper()):
                if course_key not in course_dict:
                    course_dict[course_key] = {
                        "Course": course_key,
                        "Title": course["Title"],
                        "Credits": course["Credits"],
                        "DeliveryModes": set(),
                    }
                course_dict[course_key]["DeliveryModes"].add(course["DeliveryMode"])

    final_list = [
        {
            "Course": entry["Course"],
            "Title": entry["Title"],
            "Credits": entry["Credits"],
            "DeliveryModes": list(entry["DeliveryModes"]),
        }
        for entry in course_dict.values()
    ]

    return {"courses": final_list}