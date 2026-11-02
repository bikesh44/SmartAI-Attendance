
from app import create_app
from app.models import Faculty, User
from app.extensions import db
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

app = create_app()

with app.app_context():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Faculty Details"

    headers = [
        "Faculty ID",
        "Faculty Name",
        "User ID",
        "Employee ID",
        "Designation",
        "Department ID",
        "Email",
        "Role",
        "Account Active",
        "Created At",
    ]
    sheet.append(headers)

    faculty_list = Faculty.query.order_by(Faculty.faculty_id).all()

    for faculty in faculty_list:
        user = db.session.get(User, faculty.user_id)

        sheet.append([
            faculty.faculty_id,
            user.name if user else "N/A",
            faculty.user_id,
            faculty.employee_id,
            faculty.designation,
            faculty.department_id,
            user.email if user else "N/A",
            user.role if user else "N/A",
            user.is_active if user else "N/A",
            str(user.created_at) if user and user.created_at else "",
        ])

    # Format the header row
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78"
        )
        cell.alignment = Alignment(horizontal="center")

    # Adjust column widths
    for column in sheet.columns:
        max_length = max(
            len(str(cell.value or "")) for cell in column
        )
        sheet.column_dimensions[
            get_column_letter(column[0].column)
        ].width = min(max_length + 3, 35)

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    filename = (
        f"faculty_details_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    )
    workbook.save(filename)

    print(f"Exported {len(faculty_list)} faculty records.")
    print(f"Excel file saved at: {filename}")
