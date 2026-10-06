"""Template-based generator for the five-class academic document dataset.

    python -m datasets.generate_dataset --per-class 60 --seed 42

The output is SYNTHETIC. It is deterministic (same seed -> same files) and deliberately noisy
(variable structure, optional sections, wrapped lines, casing changes, vocabulary shared between
classes) but it is still produced from templates. Results measured on it are optimistic; see
datasets/DATASET.md. Replace or extend it with real documents under datasets/real/.
"""
import argparse
import csv
import random
import textwrap
from pathlib import Path

CLASSES = ["assignment", "notice", "question_paper", "project_report", "study_material"]

# subject -> (course code, {concept: definition phrase completing "<Concept> is ...")
SUBJECTS: dict[str, tuple[str, dict[str, str]]] = {
    "Machine Learning": ("CS701", {
        "linear regression": "a supervised method that fits a straight line to predict a numeric target from input variables",
        "decision tree": "a model that splits data using a sequence of feature tests arranged as a tree",
        "overfitting": "a problem where a model memorises noise in the training data and performs poorly on new data",
        "cross-validation": "a technique that repeatedly splits the data to estimate how well a model generalises",
        "gradient descent": "an iterative optimisation algorithm that moves parameters in the direction of the steepest decrease of the loss",
        "k-means clustering": "an unsupervised algorithm that groups similar points around a fixed number of centroids",
        "confusion matrix": "a table that compares predicted classes with actual classes to show the types of errors made"}),
    "Database Management Systems": ("CS502", {
        "normalization": "the process of organising tables to reduce redundancy and update anomalies",
        "primary key": "a column or set of columns that uniquely identifies every row in a table",
        "transaction": "a sequence of database operations that must be executed as a single logical unit",
        "indexing": "a structure that speeds up the retrieval of rows by searching on selected columns",
        "SQL join": "an operation that combines rows from two or more tables based on a related column",
        "ER diagram": "a diagram that models entities, attributes and the relationships between them",
        "deadlock": "a situation in which two transactions wait for each other to release locks"}),
    "Computer Networks": ("CS503", {
        "TCP": "a connection oriented transport protocol that provides reliable ordered delivery of data",
        "IP addressing": "the scheme used to identify every host and network on the internet",
        "routing": "the process of selecting the best path for packets to travel between networks",
        "subnetting": "the division of a large network into smaller logical networks",
        "DNS": "a distributed system that translates domain names into IP addresses",
        "firewall": "a security device that filters incoming and outgoing traffic according to rules",
        "congestion control": "a set of mechanisms that prevent too much data from overloading the network"}),
    "Operating Systems": ("CS402", {
        "process scheduling": "the method by which the operating system decides which process receives the processor next",
        "virtual memory": "a technique that lets programs use more memory than is physically installed",
        "paging": "a memory management scheme that divides memory into fixed size blocks called pages",
        "semaphore": "a synchronisation variable used to control access to shared resources",
        "context switch": "the saving and restoring of process state when the processor changes tasks",
        "thread": "the smallest unit of execution that shares the resources of its parent process",
        "file system": "the part of the operating system that organises how data is stored and retrieved on disk"}),
    "Data Structures": ("CS301", {
        "linked list": "a linear collection of nodes where each node stores a value and a pointer to the next node",
        "stack": "a linear structure that follows the last in first out principle",
        "binary search tree": "a tree in which the left subtree holds smaller keys and the right subtree holds larger keys",
        "hash table": "a structure that maps keys to positions using a hash function for fast lookup",
        "graph traversal": "the systematic visiting of every vertex of a graph using breadth first or depth first search",
        "heap": "a complete binary tree that satisfies the heap ordering property",
        "queue": "a linear structure that follows the first in first out principle"}),
    "Software Engineering": ("CS601", {
        "waterfall model": "a sequential development process in which each phase is completed before the next begins",
        "agile methodology": "an iterative approach that delivers working software in short cycles with continuous feedback",
        "unit testing": "the testing of individual components in isolation to verify that they behave correctly",
        "requirements specification": "a document that describes what the software must do and the constraints it must satisfy",
        "UML diagram": "a standard visual notation used to model the structure and behaviour of software",
        "version control": "a system that records changes to files so that earlier versions can be recovered",
        "code review": "a systematic examination of source code by peers to find defects and improve quality"}),
    "Natural Language Processing": ("CS804", {
        "tokenization": "the splitting of text into smaller units such as words or sentences",
        "stemming": "a rule based reduction of words to a common root form by removing suffixes",
        "TF-IDF": "a weighting scheme that scores a term by its frequency in a document and its rarity across documents",
        "named entity recognition": "the task of locating and classifying names of people, places and organisations in text",
        "language model": "a model that assigns probabilities to sequences of words",
        "part-of-speech tagging": "the assignment of grammatical categories such as noun or verb to each word",
        "cosine similarity": "a measure of the angle between two vectors used to compare documents"}),
    "Digital Electronics": ("EC302", {
        "flip-flop": "a bistable circuit that stores one bit of information",
        "multiplexer": "a combinational circuit that selects one of many inputs and forwards it to a single output",
        "Karnaugh map": "a graphical method for simplifying Boolean expressions",
        "counter": "a sequential circuit that goes through a prescribed sequence of states on clock pulses",
        "decoder": "a combinational circuit that converts binary input codes into distinct output lines",
        "logic gate": "an elementary building block that performs a Boolean operation on one or more inputs",
        "shift register": "a group of flip-flops that moves stored bits one position on every clock pulse"}),
    "Thermodynamics": ("ME301", {
        "entropy": "a measure of the disorder or the unavailable energy of a system",
        "enthalpy": "the total heat content of a system at constant pressure",
        "Carnot cycle": "an ideal reversible cycle that gives the maximum possible efficiency between two temperatures",
        "heat engine": "a device that converts heat energy into useful mechanical work",
        "ideal gas": "a hypothetical gas whose molecules have no volume and no mutual attraction",
        "isothermal process": "a process that takes place at constant temperature",
        "first law of thermodynamics": "the statement that energy can be transformed but neither created nor destroyed"}),
    "Cloud Computing": ("CS805", {
        "virtualization": "the creation of virtual versions of hardware so that many machines share one physical server",
        "load balancing": "the distribution of incoming requests across several servers to avoid overload",
        "containers": "lightweight packages that bundle an application with its dependencies",
        "auto scaling": "the automatic adjustment of computing resources according to demand",
        "object storage": "a storage model that keeps data as objects with metadata in a flat address space",
        "serverless computing": "a model where the provider runs code on demand and manages the servers",
        "service level agreement": "a contract that defines the availability and performance a provider must deliver"}),
}

FIRST = ["Aarav", "Priya", "Rohan", "Sneha", "Karan", "Meera", "Vikram", "Anita", "Rahul", "Pooja",
         "Imran", "Neha", "Arjun", "Divya", "Sana", "Kabir", "Isha", "Nikhil"]
LAST = ["Patel", "Sharma", "Mehta", "Joshi", "Khan", "Desai", "Iyer", "Nair", "Verma", "Shah",
        "Kulkarni", "Reddy", "Bose", "Gupta"]
INSTITUTES = ["Western Technical University", "City Institute of Technology", "Greenfield College of Engineering",
              "National Institute of Applied Sciences", "Riverside University", "Horizon Engineering College"]
BRANCHES = ["Computer Engineering", "Information Technology", "Electronics Engineering",
            "Mechanical Engineering", "Electrical Engineering"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
MARK_FORMATS = ["[{m} marks]", "({m} marks)", "- {m} marks", "({m}M)", "[{m}]", "{m} marks"]
APPS = ["industry", "real world systems", "academic research", "everyday software", "engineering design"]
COMPANIES = ["TechNova Solutions", "Infra Systems", "BrightPath Software", "Orbit Analytics", "CoreWorks"]


def person(r, title=""):
    return f"{title} {r.choice(FIRST)} {r.choice(LAST)}".strip()


def date(r):
    d, m, y = r.randint(1, 28), r.randint(1, 12), r.choice([2024, 2025, 2026])
    return r.choice([f"{d} {MONTHS[m-1]} {y}", f"{d:02d}/{m:02d}/{y}", f"{MONTHS[m-1]} {d}, {y}"])


def mk(r):
    return r.choice(MARK_FORMATS).format(m=r.choice([2, 3, 4, 5, 6, 8, 10]))


def pick_subject(r):
    name = r.choice(list(SUBJECTS))
    code, concepts = SUBJECTS[name]
    return name, code, concepts


def finalize(r, text: str) -> str:
    """Add realistic extraction noise: shouting headers, deleted first line, hard-wrapped lines."""
    lines = text.split("\n")
    if r.random() < 0.15:
        lines[0] = lines[0].upper()
    if r.random() < 0.08 and len(lines) > 4:
        lines = lines[1:]
    if r.random() < 0.35:
        width = r.randint(60, 95)
        lines = [ln if len(ln) < width else textwrap.fill(ln, width) for ln in lines]
    return "\n".join(lines).strip() + "\n"


# --------------------------------------------------------------------------- assignment
ASSIGN_INSTR = [
    "Submit the assignment in neat handwriting on A4 sheets.",
    "Plagiarised work will not be accepted and will be awarded zero marks.",
    "Late submissions will lose two marks for every day of delay.",
    "Upload a single PDF file on the college portal before the deadline.",
    "Write your name, roll number and division on the first page.",
    "Attach the printed output wherever a program is required.",
    "Hand over the completed assignment to the subject teacher in the lecture.",
    "Answers should be in your own words and should not be copied from the textbook.",
    "Group submissions are not allowed; every student must submit individually.",
]
ASSIGN_TASKS = [
    "Q{i}. Explain {c1} with a suitable example. {mk}",
    "Q{i}. Write a short note on {c1} and its applications in {subj}. {mk}",
    "Q{i}. Differentiate between {c1} and {c2}. {mk}",
    "Task {i}: Prepare a one page summary of {c1} and attach it to your solved problems. {mk}",
    "Q{i}. Implement a small program that demonstrates {c1} and attach the output. {mk}",
    "{i}. Solve the problems on {c1} given in the textbook exercise and show all steps. {mk}",
    "Q{i}. Collect two real world examples of {c1} and discuss how {c2} is related to them. {mk}",
    "Q{i}. Prepare a report on {c1} covering definition, working and limitations. {mk}",
]


def make_assignment(r):
    subj, code, concepts = pick_subject(r)
    names = list(concepts)
    n = r.randint(1, 8)
    head = r.choice([f"ASSIGNMENT {n}", f"Assignment No. {n}", f"{subj} - Assignment {n}", f"Assignment {n}: {subj}"])
    meta = [f"Subject: {subj} ({code})", f"Semester: {r.randint(3, 8)}", f"Faculty: {person(r, 'Prof.')}",
            f"Last date of submission: {date(r)}", f"Total marks: {r.choice([10, 15, 20, 25])}"]
    r.shuffle(meta)
    lines = [head] + meta[: r.randint(3, 5)] + [""]
    if r.random() < 0.8:
        lines.append(r.choice(["Instructions:", "Instructions for students:", "Note:"]))
        lines += [f"- {s}" for s in r.sample(ASSIGN_INSTR, r.randint(2, 4))]
        lines.append("")
    for i in range(1, r.randint(3, 6) + 1):
        c1, c2 = r.sample(names, 2)
        lines.append(r.choice(ASSIGN_TASKS).format(i=i, c1=c1, c2=c2, subj=subj, mk=mk(r)))
    if r.random() < 0.4:
        lines += ["", "Assignments must be submitted to the subject teacher on or before the due date."]
    return finalize(r, "\n".join(lines))


# --------------------------------------------------------------------------- notice
NOTICE_EVENTS = [
    "the end semester examinations will commence from {d}",
    "the Department of {br} will organise a one day workshop on {c} on {d}",
    "the last date for payment of examination fees is {d}",
    "the library will remain closed on {d} due to maintenance work",
    "the internal examination timetable has been displayed on the notice board",
    "a campus placement drive by {co} will be conducted on {d}",
    "the institute will remain closed on {d} on account of a public holiday",
    "scholarship application forms must be submitted to the accounts section before {d}",
    "the results of the previous semester examination have been declared and are available on the student portal",
    "students with attendance below seventy five percent will not be permitted to appear for the examination",
    "the annual technical symposium will be held on {d} in the main auditorium",
    "the revised college timings will be effective from {d}",
    "the guest lecture on {c} by an invited expert is scheduled on {d}",
]
NOTICE_ACTIONS = [
    "Students are requested to take note of the above and act accordingly.",
    "Interested students should register their names with the department office.",
    "All concerned must submit the required documents before the due date.",
    "For further details, please contact the examination cell.",
    "Attendance is compulsory for all the students.",
    "Any query may be addressed to the office during working hours.",
]
NOTICE_SIGN = ["Principal", "Head of Department", "Examination Controller", "Registrar", "Dean Academics"]


def make_notice(r):
    subj, code, concepts = pick_subject(r)
    head = r.choice(["NOTICE", "CIRCULAR", "Notice", "PUBLIC NOTICE", "Notice for Students"])
    lines = [head]
    if r.random() < 0.7:
        lines.append(f"Ref No: {r.choice(['IT', 'CE', 'ADM', 'EXAM'])}/{r.choice([2024, 2025, 2026])}/{r.randint(10, 999)}")
    lines.append(f"Date: {date(r)}")
    audience = r.choice(["All students", f"All {r.choice(['first', 'second', 'third', 'final'])} year students",
                         f"All students of {r.choice(BRANCHES)}", "All students and staff members"])
    n_events = r.choice([1, 1, 2])
    for _ in range(n_events):
        ev = r.choice(NOTICE_EVENTS).format(d=date(r), br=r.choice(BRANCHES), c=r.choice(list(concepts)),
                                            co=r.choice(COMPANIES))
        lines.append(f"{audience} are hereby informed that {ev}." if _ == 0 else f"It is also informed that {ev}.")
    lines += r.sample(NOTICE_ACTIONS, r.randint(1, 2))
    lines += ["", r.choice(NOTICE_SIGN)]
    return finalize(r, "\n".join(lines))


# --------------------------------------------------------------------------- question paper
QP_INSTR = [
    "All questions are compulsory.",
    "Figures to the right indicate full marks.",
    "Draw neat labelled diagrams wherever necessary.",
    "Assume suitable data if required and state it clearly.",
    "Attempt any {k} questions from Section B.",
    "Use of a non programmable calculator is permitted.",
    "Question 1 is compulsory. Solve any three from the remaining questions.",
]
QP_SHORT = ["Define {c1}.", "What is {c1}?", "State two applications of {c1}.", "List the advantages of {c1}.",
            "Name any two features of {c1}.", "Write the purpose of {c1}.", "Differentiate between {c1} and {c2} in one line."]
QP_LONG = [
    "Explain {c1} in detail with a neat diagram.",
    "Differentiate between {c1} and {c2} with suitable examples.",
    "Describe the working of {c1}. Discuss its advantages and limitations.",
    "Write short notes on any two: {c1}, {c2}, {c3}.",
    "Discuss how {c1} is used in {subj}. Support your answer with an example.",
    "What is {c1}? Explain the steps involved and compare it with {c2}.",
    "Derive the necessary expressions for {c1} and solve a numerical example.",
]


def make_question_paper(r):
    subj, code, concepts = pick_subject(r)
    names = list(concepts)
    hours = r.choice([1, 2, 3])
    total = r.choice([30, 40, 50, 60, 70, 80, 100])
    lines = [r.choice(INSTITUTES),
             f"{r.choice(['End Semester Examination', 'Mid Semester Examination', 'Final Examination', 'Supplementary Examination'])} - {r.choice(MONTHS)} {r.choice([2024, 2025, 2026])}",
             f"Subject: {subj} ({code})", f"Time: {hours} hours", f"Maximum Marks: {total}"]
    if r.random() < 0.4:
        lines.append("Seat No: ______________")
    lines += ["", "Instructions:"]
    lines += [f"{i}. {s.format(k=r.randint(2, 4))}" for i, s in enumerate(r.sample(QP_INSTR, r.randint(2, 4)), 1)]
    lines.append("")
    qn = 1
    if r.random() < 0.6:  # sectioned paper
        lines.append(r.choice(["Section A", "SECTION A", "Part A"]) + f" (Answer the following. {r.choice([1, 2])} marks each)")
        for _ in range(r.randint(3, 5)):
            c1, c2 = r.sample(names, 2)
            lines.append(f"Q{qn}. {r.choice(QP_SHORT).format(c1=c1, c2=c2)}")
            qn += 1
        lines.append("")
        lines.append(r.choice(["Section B", "SECTION B", "Part B"]) + f" ({r.choice([5, 8, 10])} marks each)")
    for _ in range(r.randint(3, 5)):
        c1, c2, c3 = r.sample(names, 3)
        q = r.choice(QP_LONG).format(c1=c1, c2=c2, c3=c3, subj=subj)
        lines.append(f"Q{qn}. {q} {mk(r)}")
        qn += 1
    return finalize(r, "\n".join(lines))


# --------------------------------------------------------------------------- project report
SYS = ["web based application", "decision support system", "mobile application", "automated analysis tool", "monitoring system"]
GOALS = ["improve accuracy and reduce manual effort", "automate routine tasks", "support faster decisions",
         "analyse large volumes of data efficiently"]
TOOLS = ["Python and Flask", "Java and MySQL", "React and Node.js", "Python and scikit-learn", "Android Studio and Firebase"]
SOURCES = ["college records", "public repositories", "sensors installed in the laboratory", "user surveys"]
REPORT_APPS = ["Student Performance Analysis", "Library Management", "Campus Services", "Online Examination",
               "Smart Agriculture", "Healthcare Monitoring", "Traffic Analysis"]
SECTIONS = {
    "Introduction": ["In recent years {subj} has become an important part of modern engineering.",
                     "Manual processes are slow, error prone and difficult to scale.",
                     "This project aims to address these issues by using {c1}."],
    "Problem Statement": ["The existing system relies on manual effort and does not use {c1}.",
                          "As a result, users face delays and inconsistent results.",
                          "There is a need for a reliable system that applies {c2} effectively."],
    "Objectives": ["- To study existing approaches based on {c1}.", "- To design a system architecture that integrates {c2}.",
                   "- To implement and test the proposed system.", "- To evaluate performance and document the results."],
    "Literature Survey": ["Several researchers have investigated {c1} in the context of {subj}.",
                          "Earlier work proposed a method based on {c2} which improved results on benchmark data.",
                          "However, most existing work does not address scalability and usability."],
    "Methodology": ["The methodology follows requirement analysis, design, implementation and testing.",
                    "The input data is first cleaned and prepared. Then {c1} is applied to extract the required information.",
                    "Finally {c2} is used to produce the output which is displayed to the user."],
    "Implementation": ["The system is implemented using {tool}. The main modules are the input module, the processing module and the output module.",
                       "The {c1} component was implemented as a separate class so that it can be tested independently.",
                       "Screenshots of the user interface are given in Figure {k}."],
    "Results and Discussion": ["The system was tested on {n} sample inputs and produced correct output in most cases.",
                               "The results are summarised in Table {k}. The proposed approach performs better than the baseline.",
                               "Some errors occurred when the input data was incomplete."],
    "Conclusion": ["The project successfully met its objectives.",
                   "The system demonstrates that {c1} can be applied effectively to this problem.",
                   "The work also highlighted the importance of careful testing."],
    "Future Scope": ["In future the system can be extended with more data and additional features.",
                     "A mobile version and cloud deployment can be developed.",
                     "Integration of {c2} may further improve accuracy."],
}
REFS = ["[1] A. Kumar, {subj}: Principles and Practice, Tech Press, 2019.",
        "[2] R. Singh and P. Rao, \"A study of {c1}\", International Journal of Engineering Research, 2021.",
        "[3] Official documentation of {tool}."]


def make_project_report(r):
    subj, code, concepts = pick_subject(r)
    c1, c2 = r.sample(list(concepts), 2)
    tool, sysname, br = r.choice(TOOLS), r.choice(SYS), r.choice(BRANCHES)
    fmt = dict(subj=subj, c1=c1, c2=c2, tool=tool, k=r.randint(1, 9), n=r.randint(30, 500))
    lines = []
    if r.random() < 0.8:
        lines += [f"{c1.title()} Based {sysname.title()} for {r.choice(REPORT_APPS)}",
                  f"A project report submitted in partial fulfilment of the requirements for the degree of Bachelor of Engineering in {br}",
                  f"Submitted by: {person(r)}", f"Under the guidance of: {person(r, 'Prof.')}",
                  f"Department of {br}, {r.choice(INSTITUTES)}, {r.choice([2024, 2025, 2026])}", ""]
    if r.random() < 0.85:
        lines += ["Abstract",
                  f"This project presents the design and implementation of a {sysname} that applies {c1} and {c2} to {r.choice(GOALS)}. "
                  f"The system was developed using {tool} and tested on data collected from {r.choice(SOURCES)}. "
                  f"Experimental results show that the system performs {r.choice(['reliably', 'faster and more accurately', 'with acceptable accuracy'])} "
                  "compared with the existing approach. The report discusses the methodology, implementation, results and limitations of the work.", ""]
    names = [s for s in SECTIONS if s not in ("Conclusion",)]
    chosen = sorted(r.sample(names, r.randint(4, 7)), key=list(SECTIONS).index) + ["Conclusion"]
    numbered = r.random() < 0.6
    for i, sec in enumerate(chosen, 1):
        title = f"{i}. {sec}" if numbered else sec
        lines.append(title if r.random() < 0.7 else title.upper())
        body = [t.format(**fmt) for t in SECTIONS[sec]]
        lines.append("\n".join(body) if sec == "Objectives" else " ".join(body))
        lines.append("")
    if r.random() < 0.7:
        lines.append("References")
        lines += [t.format(**fmt) for t in REFS]
    return finalize(r, "\n".join(lines))


# --------------------------------------------------------------------------- study material
ELAB = ["This idea is widely used in {app}.",
        "The main advantage of {c} is that it is simple to understand and efficient in practice.",
        "Students should remember that {c} is closely related to {c2}.",
        "For example, consider a small case in {subj} where {c} is applied step by step.",
        "A common mistake is to confuse {c} with {c2}.",
        "In practice, {c} is combined with {c2} to solve larger problems.",
        "Note that {c} depends on the assumptions made about the problem."]


def make_study_material(r):
    subj, code, concepts = pick_subject(r)
    names = list(concepts)
    chosen = r.sample(names, r.randint(3, 5))
    n = r.randint(1, 9)
    lines = [r.choice([f"Unit {n}: {subj}", f"Chapter {n}: {chosen[0].title()}", f"Lecture Notes - {subj}", f"{chosen[0].title()} - Study Notes"])]
    if r.random() < 0.6:
        lines += ["", "Learning objectives"]
        lines += [f"- Define {c} and explain where it is used." for c in chosen[:2]]
    lines.append("")
    for c in chosen:
        c2 = r.choice([x for x in names if x != c])
        elab = " ".join(e.format(c=c, c2=c2, subj=subj, app=r.choice(APPS)) for e in r.sample(ELAB, r.randint(1, 3)))
        lines += [c.title() if r.random() < 0.7 else f"{c.title()}:", f"{c.capitalize()} is {concepts[c]}. {elab}", ""]
    if r.random() < 0.7:
        lines += ["Key points", f"- Remember the definition of {chosen[0]}.", f"- {chosen[1].capitalize()} is related to {chosen[-1]}.", ""]
    lines += ["Summary", f"In this unit we studied {', '.join(chosen[:-1])} and {chosen[-1]}. These ideas form the foundation for further topics in {subj}."]
    if r.random() < 0.4:
        lines += ["", "Review questions", f"1. What is {chosen[0]}?", f"2. Explain {chosen[1]} with an example."]
    return finalize(r, "\n".join(lines))


MAKERS = {
    "assignment": make_assignment, "notice": make_notice, "question_paper": make_question_paper,
    "project_report": make_project_report, "study_material": make_study_material,
}


def generate(out_dir: Path, per_class: int = 60, seed: int = 42) -> dict[str, int]:
    """Write per_class unique documents for every class and a labels.csv manifest."""
    out_dir = Path(out_dir)
    rows, counts = [], {}
    for cls in CLASSES:
        r = random.Random(f"{seed}-{cls}")  # independent stream per class
        folder = out_dir / cls
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("doc_*.txt"):
            old.unlink()
        seen: set[str] = set()
        attempts = 0
        while len(seen) < per_class:
            attempts += 1
            if attempts > per_class * 50:
                raise RuntimeError(f"Could not generate {per_class} unique '{cls}' documents")
            text = MAKERS[cls](r)
            if text in seen:
                continue
            seen.add(text)
            name = f"doc_{len(seen):03d}.txt"
            (folder / name).write_text(text, encoding="utf-8")
            rows.append((f"{cls}/{name}", cls, "generated"))
        counts[cls] = len(seen)
    with (out_dir / "labels.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "label", "source"])
        w.writerows(rows)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="datasets/raw")
    ap.add_argument("--per-class", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    counts = generate(Path(args.out), args.per_class, args.seed)
    print("Generated documents:", counts, "->", args.out)


if __name__ == "__main__":
    main()
