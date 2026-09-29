import os
import csv

def load_parsed_csvs_into_raw_meetings(mysql, folder="parsed/normalized"):
    cur = mysql.connection.cursor()

    # Clear out old data first so repeated reloads don't pile up duplicates
    cur.execute("TRUNCATE TABLE RawCourseMeetings")
    mysql.connection.commit()

    inserted = 0
    for fname in os.listdir(folder):
        if not fname.endswith(".csv"):
            continue

        with open(os.path.join(folder, fname), newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    course = row["Course"].strip()
                    section = row["Section"].strip()
                    title = row.get("Title", f"{course} Course").strip()
                    mode = row.get("DeliveryMode", "Unknown").strip()
                    credits = float(row["Credits"])
                    day = row["Day"].strip()
                    start = row["StartTime"].strip()
                    end = row["EndTime"].strip()
                    instructor = (row.get("Instructor") or "").strip()

                    cur.execute("""
                        INSERT INTO RawCourseMeetings (Course, Section, Title, DeliveryMode, Credits, Day, StartTime, EndTime, Instructor)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (course, section, title, mode, credits, day, start, end, instructor))
                    inserted += 1
                except Exception as e:
                    print(f"Skipping row in {fname} due to error: {e}")

    mysql.connection.commit()
    print(f"Inserted {inserted} rows from folder: {folder}")