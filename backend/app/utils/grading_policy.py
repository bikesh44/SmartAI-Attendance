"""
Institutional Grading Policy and Academic Calculation Module.
Smart Attendance Management System (SAMS-FR)

This module defines the authoritative institutional grading scheme, grade-point boundaries,
and decimal-safe GPA/CGPA calculations according to standard 10-point academic guidelines
(UGC / AICTE / Indian Technical Universities).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any


# Standard 10-Point Grading Scale Definition
GRADING_SCALE = [
    {
        "grade": "O",
        "description": "Outstanding",
        "min_marks": 95.0,
        "max_marks": 100.0,
        "grade_points": Decimal("10.0"),
        "status": "PASS",
    },
    {
        "grade": "A+",
        "description": "Excellent",
        "min_marks": 90.0,
        "max_marks": 94.99,
        "grade_points": Decimal("9.0"),
        "status": "PASS",
    },
    {
        "grade": "A",
        "description": "Very Good",
        "min_marks": 80.0,
        "max_marks": 89.99,
        "grade_points": Decimal("8.0"),
        "status": "PASS",
    },
    {
        "grade": "B+",
        "description": "Good",
        "min_marks": 70.0,
        "max_marks": 79.99,
        "grade_points": Decimal("7.0"),
        "status": "PASS",
    },
    {
        "grade": "B",
        "description": "Above Average",
        "min_marks": 60.0,
        "max_marks": 69.99,
        "grade_points": Decimal("6.0"),
        "status": "PASS",
    },
    {
        "grade": "C",
        "description": "Average",
        "min_marks": 50.0,
        "max_marks": 59.99,
        "grade_points": Decimal("5.0"),
        "status": "PASS",
    },
    {
        "grade": "P",
        "description": "Pass",
        "min_marks": 40.0,
        "max_marks": 49.99,
        "grade_points": Decimal("4.0"),
        "status": "PASS",
    },
    {
        "grade": "F",
        "description": "Fail",
        "min_marks": 0.0,
        "max_marks": 39.99,
        "grade_points": Decimal("0.0"),
        "status": "FAIL",
    },
]

PASSING_MIN_MARKS = 40.0
TOTAL_PROGRAM_CREDITS = 120  # Standard 4-year / lateral credit target


def determine_grade_and_points(
    marks: Optional[float],
    max_marks: float = 100.0,
    explicit_grade: Optional[str] = None,
    explicit_grade_points: Optional[float] = None,
) -> Tuple[str, Decimal, str]:
    """
    Determine the letter grade, grade points (Decimal), and status (PASS/FAIL)
    from marks or explicit values.
    """
    if explicit_grade and explicit_grade_points is not None:
        gp = Decimal(str(explicit_grade_points)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        status = "FAIL" if explicit_grade.upper() == "F" or gp == Decimal("0.0") else "PASS"
        return explicit_grade.upper(), gp, status

    if marks is None:
        return "N/A", Decimal("0.00"), "PENDING"

    # Normalize marks to 100.0 scale if max_marks != 100
    normalized_marks = float(marks)
    if max_marks and max_marks > 0 and max_marks != 100.0:
        normalized_marks = (marks / max_marks) * 100.0

    if normalized_marks < PASSING_MIN_MARKS:
        return "F", Decimal("0.00"), "FAIL"

    for entry in GRADING_SCALE:
        if normalized_marks >= entry["min_marks"]:
            # Support proportional grade points e.g. 86 marks -> 8.5, 78 marks -> 7.5
            # Or standard tier grade point
            tier_gp = entry["grade_points"]
            proportional_gp = Decimal(str(round(normalized_marks / 10.0, 1)))
            # If proportional is within tier boundaries (or close), use proportional for high fidelity
            gp = proportional_gp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return entry["grade"], gp, entry["status"]

    return "F", Decimal("0.00"), "FAIL"


def calculate_sgpa(results: List[Any]) -> Optional[float]:
    """
    Calculate Semester Grade Point Average (SGPA).
    SGPA = Sum(Credits_i * GradePoints_i) / Sum(Credits_i)
    Only considers courses where credits > 0.
    """
    total_credit_points = Decimal("0.00")
    total_credits = Decimal("0")

    for r in results:
        credits = Decimal(str(getattr(r, "credits", 0) or 0))
        if credits <= 0:
            continue

        raw_gp = getattr(r, "grade_points", 0.0)
        grade_points = Decimal(str(raw_gp or 0.0))

        total_credit_points += credits * grade_points
        total_credits += credits

    if total_credits == 0:
        return None

    sgpa = (total_credit_points / total_credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(sgpa)


def calculate_cgpa(all_results: List[Any]) -> Optional[float]:
    """
    Calculate Cumulative Grade Point Average (CGPA) across all completed semesters.
    CGPA = Sum(All Credits * All GradePoints) / Sum(All Credits)
    """
    total_credit_points = Decimal("0.00")
    total_credits = Decimal("0")

    for r in all_results:
        credits = Decimal(str(getattr(r, "credits", 0) or 0))
        if credits <= 0:
            continue

        raw_gp = getattr(r, "grade_points", 0.0)
        grade_points = Decimal(str(raw_gp or 0.0))

        total_credit_points += credits * grade_points
        total_credits += credits

    if total_credits == 0:
        return None

    cgpa = (total_credit_points / total_credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(cgpa)


def calculate_credits_earned(results: List[Any]) -> int:
    """
    Calculate total credits earned (only courses passed).
    """
    earned = 0
    for r in results:
        status = str(getattr(r, "status", "")).upper()
        if status == "PASS":
            earned += int(getattr(r, "credits", 0) or 0)
    return earned


def generate_academic_insights(
    current_gpa: Optional[float],
    cgpa: Optional[float],
    results: List[Any],
) -> List[str]:
    """
    Generate authoritative bulleted insights based on actual academic data.
    """
    insights = []

    if current_gpa is not None:
        insights.append(f"Your current semester GPA is {current_gpa:.2f}.")

    if cgpa is not None:
        insights.append(f"Your CGPA is {cgpa:.2f}.")

    valid_results = [r for r in results if getattr(r, "marks_obtained", None) is not None]
    if valid_results:
        # Highest scoring course
        highest = max(valid_results, key=lambda x: float(x.marks_obtained or 0))
        h_name = (
            getattr(highest.course, "course_name", "")
            if hasattr(highest, "course") and highest.course
            else getattr(highest, "course_name", "Highest Subject")
        )
        h_grade = getattr(highest, "grade", "A")
        insights.append(f"Highest grade in {h_name} ({h_grade}).")

        # Lowest scoring course (if multiple)
        if len(valid_results) > 1:
            lowest = min(valid_results, key=lambda x: float(x.marks_obtained or 0))
            l_name = (
                getattr(lowest.course, "course_name", "")
                if hasattr(lowest, "course") and lowest.course
                else getattr(lowest, "course_name", "Lowest Subject")
            )
            l_grade = getattr(lowest, "grade", "B")
            insights.append(f"Lowest grade in {l_name} ({l_grade}).")

    if cgpa is not None:
        if cgpa >= 8.5:
            insights.append("Outstanding academic standing. Eligible for Dean's List honors.")
        elif cgpa >= 7.5:
            insights.append("You are performing well. Keep it up!")
        elif cgpa >= 6.0:
            insights.append("Consistent academic progress across semesters.")
        else:
            insights.append("Focus on core subjects to improve overall CGPA standing.")
    elif not insights:
        insights.append("No published examination records are available yet for this semester.")

    return insights
