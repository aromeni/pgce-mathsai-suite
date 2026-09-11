"""Static Edexcel KS3/KS4 mathematics curriculum taxonomy.

This is reference data only — seeding this table never triggers AI content
generation.

`edexcel_ref` is deliberately left unset: CLAUDE.md gave two example codes
(N5, A12) and no full mapping, and an invented specification reference is
worse than an absent one. Populate from the specification if you want them.

`year_group` carries a default per topic so generation has a concrete pitch
to aim at rather than a three-year key stage. These are typical placements,
not prescriptions — a school's own scheme of work takes precedence, and the
column is editable.
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


_YEAR_GROUPS = {
    'Place value and ordering': 7,
    'Addition and subtraction': 7,
    'Multiplication and division': 7,
    'Fractions': 7,
    'Decimals': 7,
    'Percentages': 8,
    'Ratio and proportion': 8,
    'Powers and roots': 8,
    'Order of operations (BIDMAS)': 7,
    'Negative numbers': 7,
    'Introduction to algebra (expressions and terms)': 7,
    'Simplifying expressions': 7,
    'Expanding brackets': 8,
    'Factorising': 8,
    'Solving linear equations': 8,
    'Sequences (term-to-term and nth term)': 8,
    'Coordinates and straight-line graphs': 8,
    'Substitution': 7,
    'Angles (types, rules, parallel lines)': 7,
    'Properties of 2D shapes': 7,
    'Properties of 3D shapes': 7,
    'Perimeter and area': 7,
    'Volume and surface area': 8,
    'Transformations (reflection, rotation, translation, enlargement)': 8,
    'Symmetry': 7,
    'Constructions and loci': 9,
    "Pythagoras' theorem (introduction)": 9,
    'Units and measurement': 7,
    'Collecting and organising data': 7,
    'Bar charts, pie charts, pictograms': 7,
    'Mean, median, mode and range': 7,
    'Scatter graphs and correlation': 9,
    'Basic probability': 8,
    'Frequency tables and two-way tables': 8,
    'Indices and surds': 10,
    'Standard form': 10,
    'Bounds and error intervals': 11,
    'Fractions (complex operations)': 10,
    'Percentage change, reverse percentage': 10,
    'Ratio and proportion (advanced)': 10,
    'Recurring decimals': 11,
    'Expanding and factorising (advanced)': 10,
    'Quadratic equations (factorising, formula, completing the square)': 10,
    'Simultaneous equations': 10,
    'Inequalities': 10,
    'nth term of quadratic sequences': 11,
    'Functions and function notation': 11,
    'Graph transformations': 11,
    'Linear and quadratic graphs': 10,
    'Cubic and reciprocal graphs': 11,
    'Real-life graphs': 10,
    'Iteration': 11,
    'Algebraic proof': 11,
    'Direct and inverse proportion': 10,
    'Compound measures (speed, density, pressure)': 10,
    'Growth and decay': 11,
    'Rates of change from graphs': 11,
    'Circle theorems': 11,
    'Arc length and sector area': 10,
    'Pythagoras in 3D': 11,
    'Trigonometry (SOHCAHTOA)': 10,
    'Sine and cosine rules': 11,
    'Vectors': 11,
    'Congruence and similarity': 10,
    'Plans and elevations': 10,
    'Surface area and volume (advanced)': 10,
    'Bearings': 10,
    'Venn diagrams and set notation': 10,
    'Tree diagrams': 10,
    'Conditional probability': 11,
    'Cumulative frequency and box plots': 11,
    'Histograms': 11,
    'Sampling methods': 11,
    'Averages from grouped frequency tables': 10,
}


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
                    "year_group": _YEAR_GROUPS.get(topic_name),
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
                    "year_group": _YEAR_GROUPS.get(topic_name),
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
