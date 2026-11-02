import sys
sys.path.insert(0, r"c:\Users\pandi\Projects\SAMS-FR\backend")

from app import create_app
from app.extensions import db
from app.models import CourseOffering, Course, Student, Batch, Enrollment, AttendanceSession, AttendanceRecord, TimetableEntry, Faculty
from collections import defaultdict

app = create_app()
with app.app_context():
    offerings = CourseOffering.query.order_by(CourseOffering.offering_id).all()
    
    grouped = defaultdict(list)
    for o in offerings:
        grouped[(o.course_id, o.semester, o.section)].append(o)

    duplicate_slots = []
    for (cid, sem, sec), o_list in sorted(grouped.items(), key=lambda x: (x[0][1], x[0][0], x[0][2])):
        if len(o_list) > 1:
            duplicate_slots.append(((cid, sem, sec), o_list))

    print(f"Total duplicate slots: {len(duplicate_slots)}")
    
    # Analyze each of the 65 duplicate slots
    for (cid, sem, sec), o_list in duplicate_slots:
        c = o_list[0].course
        c_code = c.course_code if c else "None"
        c_name = c.course_name if c else ""
        c_batch = c.batch if c else ""
        
        # Enrolled offering
        enr_offs = [o for o in o_list if len(o.enrollments) > 0]
        # Faculty offering
        fac_offs = [o for o in o_list if o.faculty_id is not None]
        # Empty offerings
        empty_offs = [o for o in o_list if len(o.enrollments) == 0 and o.faculty_id is None and len(o.timetable_entries) == 0 and len(o.attendance_sessions) == 0]
        
        e_id = enr_offs[0].offering_id if enr_offs else None
        f_id = fac_offs[0].offering_id if fac_offs else None
        
        e_ay = enr_offs[0].academic_year if enr_offs else None
        f_ay = fac_offs[0].academic_year if fac_offs else None
        
        f_fac = fac_offs[0].faculty_id if fac_offs else None
        f_name = fac_offs[0].faculty.user.name if fac_offs and fac_offs[0].faculty and fac_offs[0].faculty.user else "None"
        
        tt_count = len(fac_offs[0].timetable_entries) if fac_offs else 0
        sess_count = len(fac_offs[0].attendance_sessions) if fac_offs else 0
        enr_count = len(enr_offs[0].enrollments) if enr_offs else 0
        
        empty_ids = [o.offering_id for o in empty_offs]
        
        print(f"Course: {c_code} ({c_name[:25]}), Sem: {sem}, Sec: {sec}, Batch: {c_batch} | Enrolled Off: {e_id} (ay='{e_ay}', enr={enr_count}) <-> Faculty Off: {f_id} (ay='{f_ay}', fac={f_fac} [{f_name}], tt={tt_count}, sess={sess_count}) | Empty Offs: {empty_ids}")
