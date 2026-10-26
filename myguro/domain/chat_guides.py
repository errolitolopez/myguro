"""How-to guides for the navigation chatbot. The steps are written here, by hand, and match the buttons
on the pages: the model only picks which guide fits the question, so it can never make up steps.
Keep them short, and change them when a button is renamed (no database, no Flask)."""

# key -> (title, what the guide is for (goes to the model), the page to start from (a TEACHER_PAGES
# key), the steps). Keys go to the model and into saved chats, so never rename one.
TEACHER_GUIDES = {
    "how-new-class": (
        "Create a class", "How to create a new class.", "classes",
        ["Open Classes.",
         "Tap New class.",
         "Type the class name (for example Grade 6 - Rizal) and, if you want, the subject.",
         "Tap Save."]),
    "how-add-students": (
        "Add students to a class", "How to put students in a class, or a whole section at once.", "classes",
        ["Open Classes, then open the class.",
         "Tap Add students.",
         "Search by name, or filter by grade and section.",
         "Tick the students, or tap Add all to add everyone shown.",
         "A student is not in the list? Only the admin can create student accounts, so ask the admin."]),
    "how-write-activity": (
        "Write an activity sheet", "How to write a new learning activity sheet with sections and questions.", "activities",
        ["Open Activities and tap New activity.",
         "Type the title and the subject, then tap Create and edit.",
         "Tap + Text section for reading material, or + Activity section for directions and questions.",
         "In an activity section add questions: multiple choice, true or false, identification, fill in the blank or short answer. Set the answer key and the points.",
         "Tap Preview to see it as students will, then Save (Ctrl+S)."]),
    "how-import-activity": (
        "Import an activity from Word", "How to make an activity sheet from a Word (.docx) file.", "activities",
        ["Open Activities and tap Import from Word.",
         "Download the Word template. Page 1 explains how to fill it in.",
         "Fill it in and keep the format, then choose your file.",
         "Check the preview. If there are problems, each one shows where it is, so fix them in Word and try again.",
         "Import it. It becomes a new draft that you can still edit."]),
    "how-give-activity": (
        "Give an activity to students", "How to assign an activity sheet to classes or to individual students, with a due date.", "activities",
        ["Open Activities and open the activity.",
         "Tap Assign.",
         "Choose the classes. Give it to everyone in the class or only to selected students, and set a due date if you want.",
         "To give it to students who are not in your classes, search for them in the same window.",
         "Tap Save. Students see it only after you open it (see the guide on opening an activity)."]),
    "how-open-activity": (
        "Open or close an activity", "How to let students start answering an activity, or stop them.", "classes",
        ["Open Classes, open the class, then open the activity to see its results page.",
         "Tap Open. Students can answer only while it is open.",
         "Tap Close when time is up. Closing submits every unfinished answer.",
         "You can open it again later."]),
    "how-check-answers": (
        "Check students' answers and release scores", "How to score short answers, change points, give another try, and show scores to students.", "classes",
        ["Open Classes, open the class, then open the activity to see its results.",
         "Tap a student to see their answers next to the answer key.",
         "Score short answers, or change the points of any question, then tap Save scores.",
         "Student did it on paper? Tap Enter paper score. Needs another try? Tap Give another try.",
         "Back on the results page, tap Release scores so students can see their scores."]),
    "how-exclude-student": (
        "Excuse an absent student from an activity", "How to exclude a student from one activity, for example when absent.", "classes",
        ["Open Classes, open the class, then open the activity to see its results.",
         "On the student's row tap Exclude. They no longer see the activity and are left out of the average.",
         "Tap Add back on that row to undo it. Their saved answers come back.",
         "A student who already submitted cannot be excluded."]),
    "how-gradebook": (
        "See the gradebook", "How to see all scores of a class in one table and download them.", "classes",
        ["Open Classes, then open the class.",
         "Tap Gradebook.",
         "Tap Export Excel or Export PDF to download it."]),
    "how-attendance": (
        "Take attendance", "How to mark present, late, absent or excused for a class, and export the record.", "classes",
        ["Open Classes, then open the class.",
         "Tap Attendance and pick the day.",
         "Mark each student, or tap All present first and change the exceptions.",
         "Tap Export to download the record for a range of days."]),
    "how-print-activity": (
        "Print or download an activity", "How to print an activity sheet, print the answer key, or download it as Word.", "activities",
        ["Open Activities and open the activity.",
         "Tap Print and choose Student copy or Answer key. It opens as a PDF to print or save.",
         "To keep or edit it, choose Word (.docx) under Download with answers. You can import that file again later."]),
    "how-delete-activity": (
        "Delete or restore an activity", "How to delete an activity sheet and how to bring a deleted one back.", "activities",
        ["Open the activity and tap Delete this activity, then confirm.",
         "A sheet nobody was given is erased. One that was given to students is archived: students lose access, but their work is kept.",
         "To bring an archived one back, open Activities and tap Deleted, then restore it. It comes back not started."]),
    "how-recovery-code": (
        "Use a recovery code", "How to make a recovery code, and how to reset a forgotten password with it.", "recovery-code",
        ["Make a code now: open Recovery code from the account menu and type your password. Write the code down, it is shown only once.",
         "Forgot your password later? On the login page tap Forgot your password?",
         "Type your username, the code and a new password.",
         "A code works 3 times. Make a new one after you use it."]),
    "how-school-year": (
        "Look at another school year", "How to switch to a past school year, which can only be looked at.", "dashboard",
        ["Open the account menu at the top right.",
         "Choose the school year in the School year box.",
         "Past years are read-only. Choose the current year again to work."]),
}
