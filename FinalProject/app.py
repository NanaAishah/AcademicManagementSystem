import streamlit as st
import pandas as pd
import os
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import base64

# ---------- Helper Functions ----------
def calculate_grade_mark(obtained, max_val):
    if max_val == 0:
        return "-", "-"
    percent = (obtained / max_val) * 100
    if percent >= 70:
        return "A", "Excellent"
    elif percent >= 60:
        return "B", "Very Good"
    elif percent >= 50:
        return "C", "Good"
    elif percent >= 45:
        return "D", "Fair"
    else:
        return "F", "Poor"

def create_pdf(school_name, school_address, student_name, student_class, student_number, term, session,
               df, total_obt, total_max, average, class_teacher_comment, principal_comment):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    normal_style.fontSize = 7
    center_style = ParagraphStyle(name="center", alignment=1, fontSize=7)

    # School Name & Address
    elements.append(Paragraph(f"<b>{school_name}</b>", ParagraphStyle(name="center_title", alignment=1, fontSize=12)))
    elements.append(Paragraph(f"{school_address}", ParagraphStyle(name="center_address", alignment=1, fontSize=10)))
    elements.append(Spacer(1, 6))
    
    # Term and Session as report title
    elements.append(Paragraph(f"<b>{term} {session} Academic Report Card</b>", 
                              ParagraphStyle(name="center_title", alignment=1, fontSize=12)))
    elements.append(Spacer(1, 12))

    # Student Info
    elements.append(Paragraph(f"Student Name: {student_name}", normal_style))
    elements.append(Paragraph(f"Class: {student_class}", normal_style))
    elements.append(Paragraph(f"No in Class: {student_number}", normal_style))
    elements.append(Spacer(1, 12))

    # Table Headers
    table_data = [
        ["Subject", "1st CA", "", "2nd CA", "", "Exam", "", "Total", "", "Grade", "Remark"],
        ["",
         Paragraph("Mark<br/>Obtained", center_style), Paragraph("Mark<br/>Obtainable", center_style),
         Paragraph("Mark<br/>Obtained", center_style), Paragraph("Mark<br/>Obtainable", center_style),
         Paragraph("Mark<br/>Obtained", center_style), Paragraph("Mark<br/>Obtainable", center_style),
         Paragraph("Mark<br/>Obtained", center_style), Paragraph("Mark<br/>Obtainable", center_style),
         "", ""]
    ]

    # Table Data Rows
    for row in df.itertuples(index=False):
        table_data.append([row.Subject,
                           row.CA1_Obt, row.CA1_Max,
                           row.CA2_Obt, row.CA2_Max,
                           row.Exam_Obt, row.Exam_Max,
                           row.Total_Obt, row.Total_Max,
                           row.Grade, row.Remark])

    col_widths = [3*cm] + [1.5*cm]*8 + [1.5*cm, 2.5*cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=2)

    # Table Style
    style = TableStyle([
        ("SPAN", (1,0),(2,0)),
        ("SPAN", (3,0),(4,0)),
        ("SPAN", (5,0),(6,0)),
        ("SPAN", (7,0),(8,0)),
        ("BACKGROUND", (0,0), (-1,1), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,1), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTNAME", (0,0), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ])

    # Red color for marks <50%
    numeric_cols = [(1,2),(3,4),(5,6),(7,8)]
    for row_idx, row in enumerate(df.itertuples(index=False), start=2):
        for obt_col, max_col in numeric_cols:
            try:
                obt = float(getattr(row, df.columns[obt_col]))
                mx = float(getattr(row, df.columns[max_col]))
                if obt < 0.5 * mx:
                    style.add('TEXTCOLOR', (obt_col,row_idx), (obt_col,row_idx), colors.red)
            except ValueError:
                continue

    table.setStyle(style)
    elements.append(table)

    # Summary
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Marks: {total_obt} / {total_max}", normal_style))
    elements.append(Paragraph(f"Average Score: {average:.2f}", normal_style))
    percentage = (total_obt / total_max) * 100 if total_max > 0 else 0
    elements.append(Paragraph(f"Percentage: {percentage:.2f}%", normal_style))

    # Comments
    elements.append(Spacer(1, 12))
    if class_teacher_comment:
        elements.append(Paragraph(f"Class Teacher's Comment: {class_teacher_comment}", normal_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Principal's Comment: {'_'*40}", normal_style))
    if principal_comment:
        elements.append(Paragraph(principal_comment, normal_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def get_ordinal_position(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# Initialize session state
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'subjects' not in st.session_state:
    st.session_state.subjects = ["Mathematics", "English"]
if 'session_id' not in st.session_state:
    st.session_state.session_id = 0

# ---------- Streamlit App ----------
st.title("📘 Report Card Generator")

progress_file = "progress_multi.csv"
school_info_file = "school_info.csv"
expected_columns = ["Student_Name", "Class", "Term", "Session", "Subject", 
                    "CA1_Obt", "CA1_Max", "CA2_Obt", "CA2_Max", 
                    "Exam_Obt", "Exam_Max", "Total_Obt", "Total_Max", "Grade", "Remark",
                    "Teacher_Comment", "Principal_Comment", "School_Name", "School_Address"]

if os.path.exists(progress_file):
    df_progress_all = pd.read_csv(progress_file)
    for col in expected_columns:
        if col not in df_progress_all.columns:
            df_progress_all[col] = ""
else:
    df_progress_all = pd.DataFrame(columns=expected_columns)

# Load school info
if os.path.exists(school_info_file):
    df_school_info = pd.read_csv(school_info_file)
    if not df_school_info.empty:
        default_school_name = df_school_info.iloc[0].get("School_Name", "Your School Name")
        default_school_address = df_school_info.iloc[0].get("School_Address", "School Address Here")
    else:
        default_school_name = "Your School Name"
        default_school_address = "School Address Here"
else:
    default_school_name = "Your School Name"
    default_school_address = "School Address Here"

# Add term and session selection
terms = ["First Term", "Second Term", "Third Term"]
# Generate sessions from 2020 to 2030
sessions = [f"{year}/{year+1}" for year in range(2020, 2031)]

tab1, tab2, tab3, tab4 = st.tabs(["Record Student Marks", "Saved Data / Export", "Overall Best Students", "Subject Best Students"])

with tab1:
    # Student Info - Select first
    student_names = df_progress_all['Student_Name'].unique().tolist() if not df_progress_all.empty else []
    student_name = st.selectbox("Select Student", options=[""] + student_names, key="student_select")
    
    # Term and Session selection
    col1, col2 = st.columns(2)
    with col1:
        term = st.selectbox("Term", options=terms, key="term_select")
    with col2:
        session = st.selectbox("Academic Session", options=sessions, key="session_select")
    
    # Check if selection has changed
    current_selection = f"{student_name}_{term}_{session}"
    if 'last_selection' not in st.session_state or st.session_state.last_selection != current_selection:
        st.session_state.session_id += 1
        st.session_state.last_selection = current_selection
        st.session_state.form_data = {}
    
    if student_name:
        # Auto-fill student information if student is selected
        # Filter by term and session as well
        student_data_filtered = df_progress_all[
            (df_progress_all["Student_Name"] == student_name) & 
            (df_progress_all["Term"] == term) &
            (df_progress_all["Session"] == session)
        ]
        
        if not student_data_filtered.empty:
            student_data = student_data_filtered.iloc[0]
            student_class = st.text_input("Class", value=student_data["Class"] if "Class" in student_data and pd.notna(student_data["Class"]) else "", key="class_input")
            student_number = st.text_input("Number in Class", value=student_data.get("Number", ""), key="number_input")
            
            # Get saved school info
            school_name = st.text_input("School Name", value=student_data.get("School_Name", default_school_name), key="school_name_input")
            school_address = st.text_input("School Address", value=student_data.get("School_Address", default_school_address), key="school_address_input")
            
            # Get saved subjects for this student, term, and session
            saved_subjects = student_data_filtered["Subject"].unique().tolist()
            
            # Get saved comments
            if not student_data_filtered.empty:
                class_teacher_comment_default = student_data_filtered.iloc[0].get("Teacher_Comment", "")
                principal_comment_default = student_data_filtered.iloc[0].get("Principal_Comment", "")
            else:
                class_teacher_comment_default = ""
                principal_comment_default = ""
        else:
            # If no data for selected term/session, try to get from any record
            student_data_any = df_progress_all[df_progress_all["Student_Name"] == student_name]
            if not student_data_any.empty:
                student_data = student_data_any.iloc[0]
                student_class = st.text_input("Class", value=student_data["Class"] if "Class" in student_data and pd.notna(student_data["Class"]) else "", key="class_input_any")
                student_number = st.text_input("Number in Class", value=student_data.get("Number", ""), key="number_input_any")
                
                # Get saved school info
                school_name = st.text_input("School Name", value=student_data.get("School_Name", default_school_name), key="school_name_input_any")
                school_address = st.text_input("School Address", value=student_data.get("School_Address", default_school_address), key="school_address_input_any")
                
                # Get saved subjects from any term/session
                saved_subjects = student_data_any["Subject"].unique().tolist()
                
                # Get saved comments
                class_teacher_comment_default = student_data.get("Teacher_Comment", "")
                principal_comment_default = student_data.get("Principal_Comment", "")
            else:
                student_class = st.text_input("Class", key="class_input_new")
                student_number = st.text_input("Number in Class", key="number_input_new")
                school_name = st.text_input("School Name", value=default_school_name, key="school_name_input_new")
                school_address = st.text_input("School Address", value=default_school_address, key="school_address_input_new")
                saved_subjects = []
                class_teacher_comment_default = ""
                principal_comment_default = ""
    else:
        # Allow entering new student name
        new_student_name = st.text_input("Enter new student name", value="", key="new_student_input")
        if new_student_name.strip():
            student_name = new_student_name.strip()
        student_class = st.text_input("Class (e.g., JSS2A)", key="class_input_new_student")
        student_number = st.text_input("Number in Class", key="number_input_new_student")
        
        # School Info for new student
        school_name = st.text_input("School Name", value=default_school_name, key="school_name_input_new_student")
        school_address = st.text_input("School Address", value=default_school_address, key="school_address_input_new_student")
        
        saved_subjects = []
        class_teacher_comment_default = ""
        principal_comment_default = ""

    # Subjects - Fixed subjects
    fixed_subjects = ["Mathematics", "English"]
    
    # Get custom subjects input
    custom_subjects_input = st.text_input("Add other subjects (comma separated)", value="", key="custom_subjects_input")
    
    # Combine subjects, ensuring no duplicates
    subjects = fixed_subjects.copy()
    
    # Add custom subjects if provided
    if custom_subjects_input:
        custom_subjects = [s.strip() for s in custom_subjects_input.split(",") if s.strip()]
        # Add only subjects that aren't already in the fixed subjects
        for subject in custom_subjects:
            if subject not in subjects:
                subjects.append(subject)
    
    # If we have saved subjects and no custom input, use saved subjects (excluding fixed ones)
    elif saved_subjects and len(saved_subjects) > 0:
        # Add saved subjects that aren't already in fixed subjects
        for subject in saved_subjects:
            if subject not in subjects:
                subjects.append(subject)

    # Store subjects in session state
    st.session_state.subjects = subjects

    # Filter previous data by term and session
    df_student_prev = df_progress_all[
        (df_progress_all["Student_Name"] == student_name) & 
        (df_progress_all["Term"] == term) &
        (df_progress_all["Session"] == session)
    ] if not df_progress_all.empty and student_name else pd.DataFrame(columns=expected_columns)

    records = []
    total_obt_all = 0
    total_max_all = 0
    
    # Use session ID for unique keys
    session_id = st.session_state.session_id
    
    for subject in subjects:
        saved_row = df_student_prev[df_student_prev['Subject'] == subject]
        ca1_obt_default = int(saved_row['CA1_Obt'].values[0]) if not saved_row.empty and saved_row['CA1_Obt'].values[0] not in ["", None] else 0
        ca1_max_default = int(saved_row['CA1_Max'].values[0]) if not saved_row.empty and saved_row['CA1_Max'].values[0] not in ["", None] else 20
        ca2_obt_default = int(saved_row['CA2_Obt'].values[0]) if not saved_row.empty and saved_row['CA2_Obt'].values[0] not in ["", None] else 0
        ca2_max_default = int(saved_row['CA2_Max'].values[0]) if not saved_row.empty and saved_row['CA2_Max'].values[0] not in ["", None] else 20
        exam_obt_default = int(saved_row['Exam_Obt'].values[0]) if not saved_row.empty and saved_row['Exam_Obt'].values[0] not in ["", None] else 0
        exam_max_default = int(saved_row['Exam_Max'].values[0]) if not saved_row.empty and saved_row['Exam_Max'].values[0] not in ["", None] else 60

        st.subheader(f"{subject}")
        col1, col2 = st.columns(2)
        with col1:
            # Use unique keys with session ID to avoid duplicates
            ca1_obt = st.number_input(f"1st CA Obtained", min_value=0, step=1, 
                                     value=st.session_state.form_data.get(f"{subject}_ca1_obt", ca1_obt_default), 
                                     key=f"{session_id}_{subject}_ca1_obt")
            ca2_obt = st.number_input(f"2nd CA Obtained", min_value=0, step=1, 
                                     value=st.session_state.form_data.get(f"{subject}_ca2_obt", ca2_obt_default), 
                                     key=f"{session_id}_{subject}_ca2_obt")
            exam_obt = st.number_input(f"Exam Obtained", min_value=0, step=1, 
                                      value=st.session_state.form_data.get(f"{subject}_exam_obt", exam_obt_default), 
                                      key=f"{session_id}_{subject}_exam_obt")
        with col2:
            ca1_max = st.number_input(f"1st CA Obtainable", min_value=1, step=1, 
                                     value=st.session_state.form_data.get(f"{subject}_ca1_max", ca1_max_default), 
                                     key=f"{session_id}_{subject}_ca1_max")
            ca2_max = st.number_input(f"2nd CA Obtainable", min_value=1, step=1, 
                                     value=st.session_state.form_data.get(f"{subject}_ca2_max", ca2_max_default), 
                                     key=f"{session_id}_{subject}_ca2_max")
            exam_max = st.number_input(f"Exam Obtainable", min_value=1, step=1, 
                                      value=st.session_state.form_data.get(f"{subject}_exam_max", exam_max_default), 
                                      key=f"{session_id}_{subject}_exam_max")

        # Store form data in session state
        st.session_state.form_data[f"{subject}_ca1_obt"] = ca1_obt
        st.session_state.form_data[f"{subject}_ca1_max"] = ca1_max
        st.session_state.form_data[f"{subject}_ca2_obt"] = ca2_obt
        st.session_state.form_data[f"{subject}_ca2_max"] = ca2_max
        st.session_state.form_data[f"{subject}_exam_obt"] = exam_obt
        st.session_state.form_data[f"{subject}_exam_max"] = exam_max

        total_obt = ca1_obt + ca2_obt + exam_obt
        total_max = ca1_max + ca2_max + exam_max
        total_obt_all += total_obt
        total_max_all += total_max
        grade, remark = calculate_grade_mark(total_obt, total_max)
        records.append([subject, ca1_obt, ca1_max, ca2_obt, ca2_max, exam_obt, exam_max, total_obt, total_max, grade, remark])

    df_student = pd.DataFrame(records, columns=["Subject", "CA1_Obt", "CA1_Max", "CA2_Obt", "CA2_Max", "Exam_Obt", "Exam_Max", "Total_Obt", "Total_Max", "Grade", "Remark"])
    average_score = df_student["Total_Obt"].mean() if len(df_student) > 0 else 0

    # Comments
    class_teacher_comment = st.text_area("Class Teacher's Comment", value=class_teacher_comment_default, key="teacher_comment")
    principal_comment = st.text_area("Principal's Comment", value=principal_comment_default, key="principal_comment")

    # Preview
    st.subheader("📄 Report Card Preview")
    st.markdown(f"**{school_name}**")
    st.markdown(f"*{school_address}*")
    st.text(f"{term} {session} Academic Report Card")
    st.text(f"Student Name: {student_name}")
    st.text(f"Class: {student_class}")
    st.text(f"No in Class: {student_number}")
    st.dataframe(df_student)
    st.text(f"Class Teacher's Comment: {class_teacher_comment}")
    st.text(f"Principal's Comment: {principal_comment}")
    st.text(f"Average Score: {average_score:.2f}")
    st.text(f"Total Marks: {total_obt_all} / {total_max_all}")
    percentage = (total_obt_all / total_max_all) * 100 if total_max_all > 0 else 0
    st.text(f"Percentage: {percentage:.2f}%")

    # Save Progress
    if st.button("💾 Save Progress", key="save_button"):
        # Save school info
        school_info_df = pd.DataFrame({
            "School_Name": [school_name],
            "School_Address": [school_address]
        })
        school_info_df.to_csv(school_info_file, index=False)
        
        # Remove existing records for this student, term, and session
        df_progress_all = df_progress_all[
            ~((df_progress_all["Student_Name"] == student_name) & 
              (df_progress_all["Term"] == term) &
              (df_progress_all["Session"] == session))
        ]
        
        # Add new records
        new_records = df_student.copy()
        new_records["Student_Name"] = student_name
        new_records["Class"] = student_class
        new_records["Term"] = term
        new_records["Session"] = session
        new_records["Teacher_Comment"] = class_teacher_comment
        new_records["Principal_Comment"] = principal_comment
        new_records["School_Name"] = school_name
        new_records["School_Address"] = school_address
        
        df_progress_all = pd.concat([df_progress_all, new_records], ignore_index=True)
        df_progress_all.to_csv(progress_file, index=False)
        st.success(f"Progress saved for {student_name} ({term}, {session})!")
        # Clear form data after saving
        st.session_state.form_data = {}

    # PDF Preview & Download
    if st.button("📥 Generate PDF & Download / Preview", key="pdf_button"):
        pdf_buffer = create_pdf(
            school_name=school_name,
            school_address=school_address,
            student_name=student_name,
            student_class=student_class,
            student_number=student_number,
            term=term,
            session=session,
            df=df_student,
            total_obt=total_obt_all,
            total_max=total_max_all,
            average=average_score,
            class_teacher_comment=class_teacher_comment,
            principal_comment=principal_comment
        )

        # PDF Preview in browser
        pdf_bytes = pdf_buffer.getvalue()
        b64 = base64.b64encode(pdf_bytes).decode()
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600px"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

        # Download button
        st.download_button("📥 Download PDF", data=pdf_buffer,
                           file_name=f"{student_name}_report_card_{term}_{session}.pdf", mime="application/pdf", key="download_button")

with tab2:
    st.subheader("Saved Progress / Export")
    
    # Filter by term and session
    col1, col2 = st.columns(2)
    with col1:
        filter_term = st.selectbox("Filter by Term", options=["All"] + terms, key="filter_term")
    with col2:
        filter_session = st.selectbox("Filter by Session", options=["All"] + sessions, key="filter_session")
    
    # Apply filters
    filtered_df = df_progress_all.copy()
    if filter_term != "All":
        filtered_df = filtered_df[filtered_df["Term"] == filter_term]
    if filter_session != "All":
        filtered_df = filtered_df[df_progress_all["Session"] == filter_session]
    
    # Pivot the data to show each student only once with their scores
    if not filtered_df.empty:
        # Create a pivot table with student names as index and subjects as columns
        pivot_df = filtered_df.pivot_table(
            index=["Student_Name", "Class", "Term", "Session"],
            columns="Subject",
            values="Total_Obt",
            aggfunc="first"
        ).reset_index()
        
        # Fill NaN values with 0 or appropriate placeholder
        pivot_df = pivot_df.fillna(0)
        
        st.dataframe(pivot_df)
        
        csv_bytes = pivot_df.to_csv(index=False).encode()
        st.download_button("Download filtered progress as CSV", data=csv_bytes,
                           file_name="filtered_student_progress.csv", mime="text/csv", key="csv_download_button")
    else:
        st.info("No data available for the selected filters.")

with tab3:
    st.subheader("Overall Best Students")
    
    # Filter by term and session
    col1, col2 = st.columns(2)
    with col1:
        best_term = st.selectbox("Term", options=terms, key="best_term")
    with col2:
        best_session = st.selectbox("Academic Session", options=sessions, key="best_session")
    
    # Calculate overall performance
    if not df_progress_all.empty:
        # Filter by selected term and session
        filtered_df = df_progress_all[
            (df_progress_all["Term"] == best_term) & 
            (df_progress_all["Session"] == best_session)
        ]
        
        if not filtered_df.empty:
            # Calculate total marks and percentage for each student
            student_totals = filtered_df.groupby(["Student_Name", "Class"]).agg({
                "Total_Obt": "sum",
                "Total_Max": "sum"
            }).reset_index()
            
            student_totals["Percentage"] = (student_totals["Total_Obt"] / student_totals["Total_Max"]) * 100
            
            # Sort by percentage in descending order
            student_totals = student_totals.sort_values("Percentage", ascending=False)
            
            # Add position column with ordinal numbers (1st, 2nd, 3rd, etc.)
            student_totals["Position"] = [get_ordinal_position(i+1) for i in range(len(student_totals))]
            
            # Format the display
            display_df = student_totals[["Position", "Student_Name", "Class", "Total_Obt", "Total_Max", "Percentage"]].copy()
            display_df["Percentage"] = display_df["Percentage"].round(2).astype(str) + "%"
            
            st.dataframe(display_df)
        else:
            st.info(f"No data available for {best_term}, {best_session}")
    else:
        st.info("No student data available yet.")

with tab4:
    st.subheader("Best Performing Students by Subject")
    
    # Filter by term and session
    col1, col2 = st.columns(2)
    with col1:
        subject_term = st.selectbox("Term", options=terms, key="subject_term")
    with col2:
        subject_session = st.selectbox("Academic Session", options=sessions, key="subject_session")
    
    # Get unique subjects
    if not df_progress_all.empty:
        # Filter by selected term and session
        filtered_df = df_progress_all[
            (df_progress_all["Term"] == subject_term) & 
            (df_progress_all["Session"] == subject_session)
        ]
        
        if not filtered_df.empty:
            subjects = filtered_df["Subject"].unique()
            selected_subject = st.selectbox("Select Subject", options=subjects, key="subject_select")
            
            # Get data for selected subject
            subject_data = filtered_df[filtered_df["Subject"] == selected_subject].copy()
            subject_data["Percentage"] = (subject_data["Total_Obt"] / subject_data["Total_Max"]) * 100
            
            # Sort by percentage in descending order
            subject_data = subject_data.sort_values("Percentage", ascending=False)
            
            # Add position column with ordinal numbers (1st, 2nd, 3rd, etc.)
            subject_data["Position"] = [get_ordinal_position(i+1) for i in range(len(subject_data))]
            
            # Format the display
            display_df = subject_data[["Position", "Student_Name", "Class", "Total_Obt", "Total_Max"]].copy()
            
            st.dataframe(display_df)
        else:
            st.info(f"No data available for {subject_term}, {subject_session}")
    else:
        st.info("No student data available yet.")