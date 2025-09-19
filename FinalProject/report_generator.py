# Simple Nigerian Report Card Generator

def get_grade_remark(total):
    if total >= 70:
        return "A", "Excellent"
    elif total >= 60:
        return "B", "Very Good"
    elif total >= 50:
        return "C", "Good"
    elif total >= 40:
        return "D", "Fair"
    else:
        return "F", "Poor"

# Subjects
subjects = ["English", "Mathematics", "Basic Science", "Business Studies"]

students = {}

num_students = int(input("Enter number of students: "))

for _ in range(num_students):
    name = input("\nEnter student name: ")
    scores = []
    total_score = 0
    
    print(f"\n--- Enter scores for {name} ---")
    for subject in subjects:
        ca1 = int(input(f"{subject} CA1 (out of 20): "))
        ca2 = int(input(f"{subject} CA2 (out of 20): "))
        exam = int(input(f"{subject} Exam (out of 60): "))
        
        total = ca1 + ca2 + exam
        grade, remark = get_grade_remark(total)
        
        scores.append([subject, ca1, ca2, exam, total, grade, remark])
        total_score += total
    
    average = total_score / len(subjects)
    percentage = (total_score / (len(subjects) * 100)) * 100
    
    students[name] = {
        "scores": scores,
        "total": total_score,
        "average": average,
        "percentage": percentage
    }

# Print report card
for name, record in students.items():
    print("\n" + "="*50)
    print(f"REPORT CARD FOR: {name}")
    print("="*50)
    print("{:<15}{:<5}{:<5}{:<6}{:<7}{:<6}{:<10}".format(
        "Subject", "CA1", "CA2", "Exam", "Total", "Grade", "Remark"
    ))
    print("-"*50)
    for s in record["scores"]:
        print("{:<15}{:<5}{:<5}{:<6}{:<7}{:<6}{:<10}".format(*s))
    
    print("-"*50)
    print(f"Total Marks: {record['total']}")
    print(f"Average: {record['average']:.2f}")
    print(f"Percentage: {record['percentage']:.2f}%")
    comment = (input("Teacher's Comment:") if record['average'] >= 50 else "Needs improvement")
    print(comment)
