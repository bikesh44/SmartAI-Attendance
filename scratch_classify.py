import sys
sys.path.insert(0, r"c:\Users\pandi\Projects\SAMS-FR\backend")

from app import create_app
from app.extensions import db
from app.models import CourseOffering, Course, Student, Batch, Enrollment, AttendanceSession, AttendanceRecord, TimetableEntry, Faculty
from collections import defaultdict

app = create_app()
with app.app_context():
    offerings = CourseOffering.query.order_by(CourseOffering.offering_id).all()
    print(f"Total offerings verified: {len(offerings)}")

    # Map of (course_id, semester, section) -> list of offerings
    grouped = defaultdict(list)
    for o in offerings:
        grouped[(o.course_id, o.semester, o.section)].append(o)

    # Let's inspect each slot and classify
    # Slots where duplicate offerings exist:
    print(f"Total distinct slots: {len(grouped)}")
    
    # Analyze pairings
    duplicate_pairs = []
    pure_stubs = []
    normal_singles = []
    ambiguous = []

    for (cid, sem, sec), o_list in sorted(grouped.items(), key=lambda x: (x[0][1], x[0][0], x[0][2])):
        c = o_list[0].course
        c_code = c.course_code if c else "None"
        c_batch = c.batch if c else ""

        if len(o_list) == 1:
            o = o_list[0]
            enr = len(o.enrollments)
            fac = o.faculty_id
            tt = len(o.timetable_entries)
            sess = len(o.attendance_sessions)
            normal_singles.append((o, c, enr, fac, tt, sess))
            continue

        # Multiple offerings in this slot
        # Check if all are empty stubs
        all_empty = all(len(o.enrollments) == 0 and o.faculty_id is None and len(o.timetable_entries) == 0 and len(o.attendance_sessions) == 0 for o in o_list)
        if all_empty:
            for o in o_list:
                pure_stubs.append((o, c))
            continue

        # Look for the enrolled offering and the faculty offering
        enrolled_offs = [o for o in o_list if len(o.enrollments) > 0]
        faculty_offs = [o for o in o_list if o.faculty_id is not None]
        empty_offs = [o for o in o_list if len(o.enrollments) == 0 and o.faculty_id is None and len(o.timetable_entries) == 0 and len(o.attendance_sessions) == 0]
        has_sess_offs = [o for o in o_list if len(o.attendance_sessions) > 0]

        # Check if exactly 1 enrolled and 1 faculty
        if len(enrolled_offs) == 1 and len(faculty_offs) == 1 and (enrolled_offs[0].offering_id != faculty_offs[0].offering_id):
            e_off = enrolled_offs[0]
            f_off = faculty_offs[0]
            duplicate_pairs.append({
                "slot": (cid, c_code, c_batch, sem, sec),
                "enrolled_offering": e_off,
                "faculty_offering": f_off,
                "empty_offerings": empty_offs,
                "sessions_on_faculty": len(f_off.attendance_sessions),
                "timetable_on_faculty": len(f_off.timetable_entries),
            })
        else:
            ambiguous.append({
                "slot": (cid, c_code, c_batch, sem, sec),
                "offerings": o_list,
                "enrolled": enrolled_offs,
                "faculty": faculty_offs,
                "empty": empty_offs,
                "sessions": has_sess_offs,
            })

    print(f"\nCategorization of duplicate slots:")
    print(f"  Standard Duplicate Pairs (1 Enrolled unassigned + 1 Faculty 2026-2027): {len(duplicate_pairs)} slots")
    print(f"  Ambiguous / Complex Multi-offering slots: {len(ambiguous)} slots")
    print(f"  Slots with purely empty stubs: {len(pure_stubs)} offerings")
    print(f"  Single offering slots: {len(normal_singles)} offerings")

    print("\n--- DETAILS OF AMBIGUOUS SLOTS ---")
    for a in ambiguous:
        cid, c_code, c_batch, sem, sec = a["slot"]
        print(f"\nAmbiguous Slot: Course={c_code} (ID={cid}, Batch={c_batch}), Sem={sem}, Sec={sec}:")
        for o in a["offerings"]:
            f_name = o.faculty.user.name if o.faculty and o.faculty.user else "Unassigned"
            print(f"  Off {o.offering_id}: AY='{o.academic_year}', Fac={o.faculty_id} ({f_name}), Enr={len(o.enrollments)}, TT={len(o.timetable_entries)}, Sess={len(o.attendance_sessions)}")
