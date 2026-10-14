
def normalize_title(title):
    return " ".join(title.casefold().split())

def detect_duplicates(tickets, category, title):
    normalized_title = normalize_title(title)

    duplicates = []

    for ticket in tickets:
        if (
            normalize_title(ticket["title"]) == normalized_title
            and ticket["category"] == category
            and ticket["status"] != "resolved"
        ):
            duplicates.append(ticket["id"])

    return duplicates


