import os
import time
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure Chrome to download files into parsed/
options = Options()
options.add_experimental_option("prefs", {
    "download.default_directory": os.path.abspath("parsed"),
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
})

# driver = webdriver.Chrome(options=options)

# # Navigate to the NJIT course schedule page
# driver.get("https://generalssb-prod.ec.njit.edu/BannerExtensibility/customPage/page/stuRegCrseSched")
# time.sleep(3)

# # Select the correct term
# dropdown = driver.find_element(By.ID, "pbid-selectBlockTermSelect")
# select = Select(dropdown)
# select.select_by_visible_text("2025 Fall")  # hardcoded for now.
# time.sleep(5)

# # Download CSVs for each subject
# wait = WebDriverWait(driver, 10)

# for i in range(0, 124):
#     spanID = f"//span[@id='pbid-subjListTableSubjectLink-{i}']/a"

#     try:
#         aTag = wait.until(EC.element_to_be_clickable((By.XPATH, spanID)))
#         aTag.click()
#     except:
#         continue

#     time.sleep(1)

#     if 80 < i < 84:
#         continue

#     if i > 14:
#         aTag.send_keys(Keys.ARROW_DOWN)
#         time.sleep(1)

#     if i < 70 or i > 114:
#         try:
#             button = wait.until(EC.element_to_be_clickable((By.ID, "pbid-courseListSectionExportToExcel")))
#             button.click()
#             time.sleep(2)
#         except:
#             continue

# driver.quit()

# ---------- NORMALIZATION BELOW ----------

DAY_MAP = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "R": "Thursday",
    "F": "Friday",
    "S": "Saturday",
    "U": "Sunday"
}

def parse_time_range(timestr):
    match = re.match(r"(\d{1,2}:\d{2} (?:AM|PM)) - (\d{1,2}:\d{2} (?:AM|PM))", timestr)
    if not match:
        return None, None
    return match.group(1), match.group(2)

def to_mysql_time(t):
    try:
        return datetime.strptime(t.strip(), "%I:%M %p").strftime("%H:%M:%S")
    except Exception:
        return ""

def normalize_csv(input_path, output_path):
    with open(input_path, newline='') as infile, open(output_path, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=[
            "Course", "Section", "Title", "DeliveryMode", "Credits", "Day", "StartTime", "EndTime", "Instructor"
        ])
        writer.writeheader()

        for row in reader:
            course = row.get("Course", "").strip()
            section = row.get("Section", "").strip()
            title = row.get("Title", "").strip()
            delivery = row.get("Delivery Mode", "").strip()
            instructor = row.get("Instructor", "").strip()


            raw_credits = row.get("Credits", "").strip()
            try:
                credits = float(raw_credits or 0)
            except Exception as e:
                print(f"[ERROR] {e} → credits='{raw_credits}' in file {input_path}")
                print("Full row:", row)
                raise



            days = row.get("Days", "").strip()
            times = row.get("Times", "").strip()

            start, end = "", ""
            day_chars = list(days) if days else []

            if times:
                start_raw, end_raw = parse_time_range(times)
                start = to_mysql_time(start_raw)
                end = to_mysql_time(end_raw)

            if day_chars:
                for d in day_chars:
                    if d not in DAY_MAP or not start or not end:
                        continue
                    writer.writerow({
                        "Course": course,
                        "Section": section,
                        "Title": title,
                        "DeliveryMode": delivery,
                        "Credits": credits,
                        "Day": DAY_MAP[d],
                        "StartTime": start,
                        "EndTime": end,
                        "Instructor": instructor
                    })
            else:
                writer.writerow({
                    "Course": course,
                    "Section": section,
                    "Title": title,
                    "DeliveryMode": delivery,
                    "Credits": credits,
                    "Day": "",
                    "StartTime": "",
                    "EndTime": "",
                    "Instructor": instructor
                })

# Normalize all files in parsed/ to parsed/normalized/
input_folder = "parsed"
output_folder = os.path.join(input_folder, "normalized")
os.makedirs(output_folder, exist_ok=True)

for fname in os.listdir(input_folder):
    if not fname.endswith(".csv"):
        continue
    input_path = os.path.join(input_folder, fname)
    output_path = os.path.join(output_folder, fname)
    normalize_csv(input_path, output_path)
    print(f"Normalized {fname}")