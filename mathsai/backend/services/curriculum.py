"""Static Edexcel KS3/KS4 mathematics curriculum taxonomy.

This is reference data only — seeding this table never triggers AI content
generation. `edexcel_ref` and `difficulty_band` are left unset where CLAUDE.md
did not specify exact codes/tiers; the teacher can refine these later.
"""

import logging

from sqlalchemy.orm import Session

from models import Topic

logger = logging.getLogger("mathsai")

_KS3_NUMBER = [
    "Place value and ordering",
    "Addition and subtraction",
    "Multiplication and division",
    "Fractions",
    "Decimals",
    "Percentages",
    "Ratio and proportion",
    "Powers and roots",
    "Order of operations (BIDMAS)",
    "Negative numbers",
]

_KS3_ALGEBRA = [
    "Introduction to algebra (expressions and terms)",
    "Simplifying expressions",
    "Expanding brackets",
    "Factorising",
    "Solving linear equations",
    "Sequences (term-to-term and nth term)",
    "Coordinates and straight-line graphs",
    "Substitution",
]

_KS3_GEOMETRY = [
    "Angles (types, rules, parallel lines)",
    "Properties of 2D shapes",
    "Properties of 3D shapes",
    "Perimeter and area",
    "Volume and surface area",
    "Transformations (reflection, rotation, translation, enlargement)",
    "Symmetry",
    "Constructions and loci",
    "Pythagoras' theorem (introduction)",
    "Units and measurement",
]

_KS3_STATISTICS = [
    "Collecting and organising data",
    "Bar charts, pie charts, pictograms",
    "Mean, median, mode and range",
    "Scatter graphs and correlation",
    "Basic probability",
    "Frequency tables and two-way tables",
]

_KS4_NUMBER = [
    "Indices and surds",
    "Standard form",
    "Bounds and error intervals",
    "Fractions (complex operations)",
    "Percentage change, reverse percentage",
    "Ratio and proportion (advanced)",
    "Recurring decimals",
]

_KS4_ALGEBRA = [
    "Expanding and factorising (advanced)",
    "Quadratic equations (factorising, formula, completing the square)",
    "Simultaneous equations",
    "Inequalities",
    "nth term of quadratic sequences",
    "Functions and function notation",
    "Graph transformations",
    "Linear and quadratic graphs",
    "Cubic and reciprocal graphs",
    "Real-life graphs",
    "Iteration",
    "Algebraic proof",
]

_KS4_RATIO_PROPORTION = [
    "Direct and inverse proportion",
    "Compound measures (speed, density, pressure)",
    "Growth and decay",
    "Rates of change from graphs",
]

_KS4_GEOMETRY = [
    "Circle theorems",
    "Arc length and sector area",
    "Pythagoras in 3D",
    "Trigonometry (SOHCAHTOA)",
    "Sine and cosine rules",
    "Vectors",
    "Congruence and similarity",
    "Plans and elevations",
    "Surface area and volume (advanced)",
    "Bearings",
]

_KS4_PROBABILITY_STATISTICS = [
    "Venn diagrams and set notation",
    "Tree diagrams",
    "Conditional probability",
    "Cumulative frequency and box plots",
    "Histograms",
    "Sampling methods",
    "Averages from grouped frequency tables",
]


def _build_taxonomy() -> list[dict]:
    taxonomy: list[dict] = []

    ks3_strands = {
        "Number": _KS3_NUMBER,
        "Algebra": _KS3_ALGEBRA,
        "Geometry and Measures": _KS3_GEOMETRY,
        "Statistics and Probability": _KS3_STATISTICS,
    }
    for strand, topic_names in ks3_strands.items():
        for topic_name in topic_names:
            taxonomy.append(
                {
                    "key_stage": "KS3",
                    "strand": strand,
                    "topic_name": topic_name,
                    "edexcel_ref": None,
                    "difficulty_band": "Both",
                }
            )

    ks4_strands = {
        "Number": _KS4_NUMBER,
        "Algebra": _KS4_ALGEBRA,
        "Ratio, Proportion and Rates of Change": _KS4_RATIO_PROPORTION,
        "Geometry and Measures": _KS4_GEOMETRY,
        "Probability and Statistics": _KS4_PROBABILITY_STATISTICS,
    }
    for strand, topic_names in ks4_strands.items():
        for topic_name in topic_names:
            taxonomy.append(
                {
                    "key_stage": "KS4",
                    "strand": strand,
                    "topic_name": topic_name,
                    "edexcel_ref": None,
                    "difficulty_band": None,
                }
            )

    return taxonomy


CURRICULUM_TAXONOMY = _build_taxonomy()


def seed_topics(db: Session) -> None:
    """Populate the topics table from the static taxonomy if empty.

    Idempotent: does nothing if topics already exist. Never calls the
    Anthropic API — this seeds curriculum metadata only.
    """
    existing_count = db.query(Topic).count()
    if existing_count > 0:
        logger.info("Topics table already seeded (%d rows) — skipping.", existing_count)
        return

    topics = [Topic(**entry) for entry in CURRICULUM_TAXONOMY]
    db.bulk_save_objects(topics)
    db.commit()
    logger.info("Seeded %d curriculum topics.", len(topics))
