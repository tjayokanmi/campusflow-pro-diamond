"""Engineering Knowledge Lab for CampusFlow Pro."""

import json
from datetime import datetime, timezone
from pathlib import Path


QUESTIONS = [
    {
        "question": "Is a critical ticket overdue exactly 60 minutes after creation?",
        "options": {
            "A": "Yes, exactly at 60 minutes",
            "B": "No, only strictly after its deadline",
            "C": "Only if it is assigned",
            "D": "Only after escalation",
        },
        "answer": "B",
        "topic": "SLA boundaries",
    },
    {
        "question": "What priority applies to a low-urgency ticket affecting 10 users?",
        "options": {
            "A": "Low",
            "B": "High",
            "C": "Medium",
            "D": "Critical",
        },
        "answer": "B",
        "topic": "Priority calculation",
    },
    {
        "question": "What happens when an unassigned open ticket is moved to in_progress?",
        "options": {
            "A": "The transition succeeds",
            "B": "The ticket is automatically assigned",
            "C": "The operation is rejected without mutation",
            "D": "The ticket becomes resolved",
        },
        "answer": "C",
        "topic": "Workflow validation",
    },
    {
        "question": "What happens when a resolved high-priority ticket is reopened?",
        "options": {
            "A": "The original SLA deadline remains",
            "B": "A fresh SLA cycle starts and created_at is preserved",
            "C": "A new ticket ID is generated",
            "D": "The ticket becomes in_progress",
        },
        "answer": "B",
        "topic": "SLA lifecycle",
    },
    {
        "question": "What happens if escalation is checked three times in the same cycle?",
        "options": {
            "A": "Three escalation events are recorded",
            "B": "The ticket is deleted",
            "C": "Only one escalation event is recorded",
            "D": "The priority is reduced",
        },
        "answer": "C",
        "topic": "Escalation idempotency",
    },
    {
        "question": "What should happen when the system loads corrupted JSON?",
        "options": {
            "A": "Replace the existing data with an empty list",
            "B": "Ignore the error",
            "C": "Delete the file",
            "D": "Reject the load and preserve the current state",
        },
        "answer": "D",
        "topic": "Persistence safety",
    },
    {
        "question": "A PR changes SLA calculations but lacks boundary tests. What should the reviewer do?",
        "options": {
            "A": "Approve immediately",
            "B": "Request boundary tests and an explanation",
            "C": "Merge and test later",
            "D": "Ignore the missing tests",
        },
        "answer": "B",
        "topic": "Code review",
    },
    {
        "question": "An AI suggests using eval() to load JSON. What should you do?",
        "options": {
            "A": "Use eval() because it is shorter",
            "B": "Disable validation",
            "C": "Reject it and use JSON parsing with validation",
            "D": "Trust the AI suggestion",
        },
        "answer": "C",
        "topic": "AI evaluation and security",
    },
    {
        "question": "What should happen when a new ticket matches an unresolved ticket's normalized title and category?",
        "options": {
            "A": "Automatically delete the existing ticket",
            "B": "Warn the user and request confirmation",
            "C": "Automatically resolve the existing ticket",
            "D": "Create the new ticket silently",
        },
        "answer": "B",
        "topic": "Duplicate detection",
    },
    {
        "question": "What happens to audit event count after a rejected status operation?",
        "options": {
            "A": "It increases by one",
            "B": "It increases by two",
            "C": "All events are deleted",
            "D": "It remains unchanged",
        },
        "answer": "D",
        "topic": "Audit integrity",
    },
]


def get_valid_answer():
    """Accept only A, B, C, or D."""
    while True:
        answer = input("Your answer (A/B/C/D): ").strip().upper()

        if answer in ("A", "B", "C", "D"):
            return answer

        print("[Error] Enter A, B, C, or D.")


def calculate_score(questions, answers):
    """Calculate the quiz score."""
    if len(questions) != len(answers):
        raise ValueError("Every question must have an answer")

    return sum(
        answer == question["answer"]
        for question, answer in zip(questions, answers)
    )


def save_quiz_session(session, path="data/quiz_sessions.json"):
    """Append a quiz session to a JSON file."""

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        with file_path.open("r", encoding="utf-8") as file:
            sessions = json.load(file)

        if not isinstance(sessions, list):
            raise ValueError("Quiz storage must contain a list")
    else:
        sessions = []

    sessions.append(session)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(sessions, file, indent=4)


def run_knowledge_lab():
    """Run the interactive engineering quiz."""

    print("\n--- Engineering Knowledge Lab ---")

    while True:
        participant = input(
            "Select participant (A/B): "
        ).strip().upper()

        if participant in ("A", "B"):
            break

        print("[Error] Select Engineer A or Engineer B.")

    answers = []
    explanations = {}

    for index, question in enumerate(QUESTIONS, start=1):
        print(f"\nQuestion {index}: {question['question']}")

        for letter, option in question["options"].items():
            print(f"  {letter}. {option}")

        answer = get_valid_answer()
        answers.append(answer)

        if index in (1, 5, 8):
            while True:
                explanation = input(
                    "Explain your answer (1-2 sentences): "
                ).strip()

                if explanation:
                    explanations[str(index)] = explanation
                    break

                print("[Error] An explanation is required.")

    score = calculate_score(QUESTIONS, answers)

    weak_topics = [
        question["topic"]
        for question, answer in zip(QUESTIONS, answers)
        if answer != question["answer"]
    ]

    session = {
        "participant": f"Engineer {participant}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "choices": answers,
        "score": score,
        "explanations": explanations,
    }

    save_quiz_session(session)

    print("\n--- Quiz Results ---")
    print(f"Participant: Engineer {participant}")
    print(f"Score: {score}/10")

    if weak_topics:
        print("Topics to review:")
        for topic in weak_topics:
            print(f"  - {topic}")
    else:
        print("Excellent! No weak topics identified.")

    print("\nAnswer Review:")
    for index, (question, answer) in enumerate(
        zip(QUESTIONS, answers), start=1
    ):
        correct = question["answer"]
        result = "Correct" if answer == correct else "Incorrect"

        print(
            f"Q{index}: Your answer: {answer} | "
            f"Correct: {correct} | {result}"
        )

        if str(index) in explanations:
            print(f"  Explanation: {explanations[str(index)]}")

    print("\nQuiz session saved successfully.")

    return session