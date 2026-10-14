import unittest

from campusflow.knowledge_lab import QUESTIONS, calculate_score


class TestKnowledgeLab(unittest.TestCase):

    def test_perfect_score(self):
        answers = [question["answer"] for question in QUESTIONS]

        self.assertEqual(
            calculate_score(QUESTIONS, answers),
            10,
        )

    def test_all_wrong_answers(self):
        answers = [
            next(
                option for option in ("A", "B", "C", "D")
                if option != question["answer"]
            )
            for question in QUESTIONS
        ]

        self.assertEqual(
            calculate_score(QUESTIONS, answers),
            0,
        )

    def test_incomplete_answers_rejected(self):
        with self.assertRaises(ValueError):
            calculate_score(QUESTIONS, ["A", "B"])


if __name__ == "__main__":
    unittest.main()