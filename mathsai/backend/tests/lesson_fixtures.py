"""Valid schema-version-2 lesson content, shared by the test modules.

Split into the three fragments the three concurrent generation calls return,
plus the merged result. Kept in one place so the shape only has to be
corrected once when the lesson schema changes again.
"""

CORE_FRAGMENT = {
    "topic_introduction": {
        "what_it_is": "Solving equations with the unknown on both sides.",
        "why_it_matters": "Balancing is the idea behind rearranging any formula.",
        "prior_knowledge_needed": ["Collecting like terms", "Inverse operations"],
        "leads_on_to": ["Simultaneous equations", "Rearranging formulae"],
        "learning_objectives": ["Solve equations with unknowns on both sides"],
        "success_criteria": ["I can collect the unknowns on one side"],
    },
    "i_do": [
        {
            "title": "Example 1 — unknown on both sides",
            "problem": "5x + 3 = 3x + 11",
            "steps": [
                {
                    "working": "5x + 3 - 3x = 3x + 11 - 3x",
                    "narration": "I subtract 3x from both sides to gather the x terms.",
                },
                {"working": "2x + 3 = 11", "narration": "Now it looks familiar."},
            ],
            "key_teaching_point": "Whatever we do to one side we do to the other.",
            "requires_diagram": False,
            "diagram_description": None,
        }
    ],
    "we_do": [
        {
            "title": "Guided 1",
            "problem": "7x - 2 = 4x + 10",
            "scaffolded_working": "Step 1: 3x - 2 = 10\nStep 2: ________",
            "faded_from_step": 2,
            "questions_to_ask": ["What do we do to undo the subtraction?"],
            "full_answer": "x = 4",
            "requires_diagram": False,
            "diagram_description": None,
        }
    ],
}

SUPPORT_FRAGMENT = {
    "starter": {
        "retrieval_focus": "Collecting like terms and inverse operations.",
        "questions": [
            {
                "question": "Simplify 5x - 3x",
                "answer": "2x",
                "prerequisite": "Collecting like terms",
                "tier": "Fluency",
            }
        ],
    },
    "key_vocabulary": [
        {
            "term": "equation",
            "definition": "A statement that two expressions are equal.",
            "everyday_meaning": None,
            "notation": "=",
        }
    ],
    "common_errors": [
        {
            "error": "Subtracting from one side only",
            "why_it_happens": "Pupils treat the equation as an instruction, not a balance.",
            "correction": "Show both sides changing together.",
            "address_at": "During the first modelled example.",
        }
    ],
    "plenary": [
        {
            "question": "Solve 6x + 1 = 2x + 9",
            "answer": "x = 2",
            "checks": "Whether they gather unknowns before constants.",
        }
    ],
}

ADAPTIVE_FRAGMENT = {
    "adaptive_teaching": {
        "scaffolds": [
            {
                "barrier": "Loses track of which side has been changed",
                "scaffold": "Two-column recording sheet, one column per side",
                "remove_when": "Three consecutive correct solutions without it",
            }
        ],
        "concrete_representations": [
            {
                "resource": "Algebra tiles",
                "how_to_use": "Build both sides, remove matching tiles in pairs.",
                "bridge_to_abstract": "Record each removal as a written line.",
            }
        ],
        "language_support": {
            "tier_2_vocabulary": [
                {"word": "balance", "meaning_in_context": "Both sides stay equal."}
            ],
            "false_friends": [
                {
                    "word": "solution",
                    "everyday_meaning": "A liquid mixture, or a fix to a problem",
                    "maths_meaning": "The value of the unknown that makes it true",
                }
            ],
            "sentence_stems": ["I subtracted ___ from both sides because ___"],
            "reduced_language_versions": [
                {
                    "original": "Ravi thinks of a number, multiplies it by five ...",
                    "reworded": "5x + 3 = 3x + 11. Work out x.",
                }
            ],
        },
        "stretch": ["Always, sometimes, never: an equation has exactly one solution."],
    }
}

VALID_LESSON_RAW = {**CORE_FRAGMENT, **SUPPORT_FRAGMENT, **ADAPTIVE_FRAGMENT}

# Marker phrases identifying which of the three prompts a mocked call
# received, so a client-level mock can answer with the right fragment
# regardless of the order the concurrent calls happen to arrive in.
PART_MARKERS = {
    "Produce the teaching sequence": CORE_FRAGMENT,
    "Produce the supporting material": SUPPORT_FRAGMENT,
    "Produce the adaptive teaching plan": ADAPTIVE_FRAGMENT,
}
