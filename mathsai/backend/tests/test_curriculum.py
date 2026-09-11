"""Phase 1 — curriculum seed data."""

from models import Topic
from services.curriculum import CURRICULUM_TAXONOMY, seed_topics


def test_seed_topics_populates_full_taxonomy(db_session):
    seed_topics(db_session)
    count = db_session.query(Topic).count()
    assert count == len(CURRICULUM_TAXONOMY)
    assert count == 74


def test_seed_topics_is_idempotent(db_session):
    seed_topics(db_session)
    seed_topics(db_session)
    assert db_session.query(Topic).count() == len(CURRICULUM_TAXONOMY)


def test_seed_topics_covers_both_key_stages_and_all_strands(db_session):
    seed_topics(db_session)
    topics = db_session.query(Topic).all()

    key_stages = {t.key_stage for t in topics}
    strands = {t.strand for t in topics}

    assert key_stages == {"KS3", "KS4"}
    assert strands == {
        "Number",
        "Algebra",
        "Geometry and Measures",
        "Statistics and Probability",
        "Ratio, Proportion and Rates of Change",
        "Probability and Statistics",
    }


def test_seed_topics_never_calls_ai(db_session, monkeypatch):
    """Seeding is static reference data — it must never touch ai_service."""
    from services import ai_service

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("seed_topics must never call the Anthropic API")

    monkeypatch.setattr(ai_service, "generate_lesson", _fail_if_called)
    monkeypatch.setattr(ai_service, "generate_questions", _fail_if_called)

    seed_topics(db_session)  # should not raise
    assert db_session.query(Topic).count() == 74


def test_every_topic_has_a_year_group():
    """A missing year leaves generation pitched at "unspecified" across a
    three-year key stage."""
    missing = [e["topic_name"] for e in CURRICULUM_TAXONOMY if e.get("year_group") is None]
    assert not missing, f"topics without a year group: {missing}"


def test_seed_backfills_year_group_on_an_already_seeded_table(db_session):
    """seed_topics only inserts into an empty table, so a database seeded
    before the column existed would keep year_group NULL forever after the
    migration. The backfill is what stops that being silent."""
    seed_topics(db_session)
    db_session.query(Topic).update({Topic.year_group: None})
    db_session.commit()
    assert db_session.query(Topic).filter(Topic.year_group.is_(None)).count() > 0

    seed_topics(db_session)

    assert db_session.query(Topic).filter(Topic.year_group.is_(None)).count() == 0


def test_backfill_is_idempotent(db_session):
    seed_topics(db_session)
    before = {t.id: t.year_group for t in db_session.query(Topic).all()}
    seed_topics(db_session)
    after = {t.id: t.year_group for t in db_session.query(Topic).all()}
    assert before == after
