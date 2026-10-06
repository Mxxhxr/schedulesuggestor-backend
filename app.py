import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from retrieveCourses import retrieve_courses, load_courses_into_schedule_tables
from generateSchedule import generate_schedule
from dataLoader import load_parsed_csvs_into_raw_meetings

load_dotenv()  # was imported but never called before — .env was silently ignored

app = Flask(__name__)
CORS(app)


# MySQL config

# AWS RDS config (Maahir's own account):
app.config["MYSQL_USER"] = "admin"
app.config["MYSQL_PASSWORD"] = os.environ.get("sqlpass")
app.config["MYSQL_HOST"] = "schedule-suggestor-db.c1cwew8yw4od.us-east-2.rds.amazonaws.com"
app.config["MYSQL_DB"] = "schedule_suggestor"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

# local config (uncomment this block and comment the AWS block above to
# develop against your local MySQL instead):
# app.config["MYSQL_USER"] = "root"
# app.config["MYSQL_PASSWORD"] = "2002"
# app.config["MYSQL_HOST"] = "localhost"
# app.config["MYSQL_DB"] = "schedule_suggestor"
# app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)
with app.app_context():
    load_courses_into_schedule_tables(mysql)  # load courses into schedule tables on startup

@app.route("/")
def index():
    return "Schedule Suggestor"

@app.route("/reload-data", methods=["POST"])
def reload_data():
    try:
        load_parsed_csvs_into_raw_meetings(mysql)
        load_courses_into_schedule_tables(mysql) # load raw data into course section + section meeting tables
        return jsonify({"status": "Reload complete", "details": "Both raw and structured tables updated"}), 200
    except Exception as e:
        return jsonify({"Error": str(e)}), 500

@app.route("/courses")
def all_courses():
    result = retrieve_courses(None, mysql)
    return jsonify(result)

@app.route("/courses/<course_name>")
def courses(course_name):
    result = retrieve_courses(course_name, mysql)
    return jsonify(result)

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(force=True)
        selected_courses = data.get("selectedCourses", [])
        time_preferences = data.get("timePreferences", {})

        print("Selected:", selected_courses)
        print("Prefs:", time_preferences)


        result = generate_schedule(selected_courses, time_preferences, mysql=mysql)
        return jsonify(result)
    except Exception as e:
        print("Error in /generate", e)
        return jsonify({"error": "Invalid request", "details": str(e)}), 400

if __name__ == "__main__":
    app.run(port=5000, debug=True)