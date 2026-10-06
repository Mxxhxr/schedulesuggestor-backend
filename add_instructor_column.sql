-- Run this once against your existing local database to add the
-- Instructor column that wasn't there originally.
USE schedule_suggestor;

ALTER TABLE RawCourseMeetings ADD COLUMN Instructor VARCHAR(255);
ALTER TABLE CourseSections ADD COLUMN instructor VARCHAR(255);
