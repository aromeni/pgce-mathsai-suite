"""PDF and print export routes (CLAUDE.md API Routes — Export Router).

Content is fetched through cache_service exactly like the Lessons/Questions
routers (cache hit, or lazily generate-and-cache on miss), then rendered to
print-friendly HTML and converted to PDF via WeasyPrint. AI-generated text
fields are HTML-escaped before interpolation — maths content routinely
contains "<"/">" (inequalities), which would otherwise be mistaken for
stray tags by the HTML/PDF renderer.
"""

import html
import logging
import re

import markdown as md
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from weasyprint import HTML as WeasyHTML

from database import get_db
from models import Topic
from services import cache_service
from services.ai_service import AIGenerationError

logger = logging.getLogger("mathsai")

router = APIRouter(prefix="/api/export", tags=["export"])

DIFFICULTY_TIERS = ["Foundation", "Developing", "Extending"]

esc = html.escape

PDF_STYLE = """
<style>
  @page {
    size: A4;
    margin: 2cm;
    @bottom-center { content: "MathsAI — page " counter(page) " of " counter(pages);
                     font-size: 8pt; color: #666; }
  }
  body { font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a;
         font-size: 11pt; line-height: 1.5; }
  h1 { font-family: Helvetica, Arial, sans-serif; font-size: 20pt;
       border-bottom: 2px solid #0d9488; padding-bottom: 6px; }
  h2 { font-family: Helvetica, Arial, sans-serif; font-size: 14pt;
       color: #0d9488; margin-top: 1.4em; }
  h3, h4 { font-family: Helvetica, Arial, sans-serif; margin-top: 1.1em; }
  .meta { color: #555; font-size: 9pt; margin-bottom: 1em; }
  table { width: 100%; border-collapse: collapse; margin: 0.8em 0; }
  th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left;
           vertical-align: top; font-size: 10pt; }
  th { background: #f0f0f0; }
  .example, .error-card, .question-card {
    border: 1px solid #ccc; border-radius: 6px; padding: 10px 12px;
    margin: 0.6em 0; break-inside: avoid;
  }
  .example h4, .question-card h4 { margin: 0 0 6px 0; font-size: 11pt; color: #0d9488; }
  .tier-badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
                font-size: 9pt; font-weight: bold; }
  .tier-Foundation { background: #dcfce7; color: #166534; }
  .tier-Developing { background: #fef9c3; color: #854d0e; }
  .tier-Extending { background: #fee2e2; color: #991b1b; }
  .answer { background: #f7f7f7; border-left: 3px solid #0d9488;
            padding: 6px 10px; margin-top: 6px; font-size: 10pt; }
  .tier-section { page-break-before: always; }
  .tier-section:first-of-type { page-break-before: avoid; }
</style>
"""


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _get_topic_or_404(db: Session, topic_id: int) -> Topic:
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    return topic


def _topic_header_html(topic: Topic) -> str:
    ref = f" &middot; {esc(topic.edexcel_ref)}" if topic.edexcel_ref else ""
    return f"""
      <h1>{esc(topic.topic_name)}</h1>
      <p class="meta">{esc(topic.key_stage)} &middot; {esc(topic.strand)}{ref}</p>
    """


def _render_pdf(html_body: str) -> bytes:
    try:
        return WeasyHTML(
            string=f"<html><head>{PDF_STYLE}</head><body>{html_body}</body></html>"
        ).write_pdf()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — any renderer failure is a 500 per CLAUDE.md
        logger.error("PDF generation failed: %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=500, detail="PDF generation failed") from exc


def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/lesson/{topic_id}/pdf")
def export_lesson_pdf(topic_id: int, db: Session = Depends(get_db)):
    topic = _get_topic_or_404(db, topic_id)
    try:
        lesson = cache_service.get_lesson(db, topic_id)
    except cache_service.TopicNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    except AIGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    notes_html = md.markdown(lesson["lesson_notes"])

    examples_html = "".join(
        f"""<div class="example">
              <h4>{esc(e['title'])}</h4>
              <p><strong>Problem:</strong> {esc(e['problem'])}</p>
              <p><strong>Solution:</strong> {esc(e['solution'])}</p>
              <p><em>Teaching note: {esc(e['teaching_note'])}</em></p>
            </div>"""
        for e in lesson["worked_examples"]
    )

    vocab_rows = "".join(
        f"<tr><td>{esc(v['term'])}</td><td>{esc(v['definition'])}</td></tr>"
        for v in lesson["key_vocabulary"]
    )
    vocab_html = (
        f"<h2>Key Vocabulary</h2><table><thead><tr><th>Term</th>"
        f"<th>Definition</th></tr></thead><tbody>{vocab_rows}</tbody></table>"
        if lesson["key_vocabulary"]
        else ""
    )

    errors_html = "".join(
        f"""<div class="error-card">
              <p><strong>Misconception:</strong> {esc(c['error'])}</p>
              <p><strong>Correction:</strong> {esc(c['correction'])}</p>
            </div>"""
        for c in lesson["common_errors"]
    )
    errors_section = f"<h2>Common Errors</h2>{errors_html}" if lesson["common_errors"] else ""

    body = (
        _topic_header_html(topic)
        + notes_html
        + (f"<h2>Worked Examples</h2>{examples_html}" if examples_html else "")
        + vocab_html
        + errors_section
    )

    pdf_bytes = _render_pdf(body)
    filename = f"lesson-{topic.id}-{_slugify(topic.topic_name)}.pdf"
    return _pdf_response(pdf_bytes, filename)


def _question_card_html(q: dict) -> str:
    options_html = ""
    if q.get("options"):
        options_html = "<ul>" + "".join(f"<li>{esc(o)}</li>" for o in q["options"]) + "</ul>"
    marks = q["marks"]
    return f"""
      <div class="question-card">
        <h4>Question {q['question_number']} ({marks} mark{'' if marks == 1 else 's'})</h4>
        <p>{esc(q['question_text'])}</p>
        {options_html}
        <div class="answer">
          <p><strong>Answer:</strong> {esc(q['answer'])}</p>
          <p><strong>Mark scheme:</strong> {esc(q['mark_scheme'])}</p>
        </div>
      </div>
    """


@router.get("/questions/{topic_id}/pdf")
def export_questions_pdf(topic_id: int, db: Session = Depends(get_db)):
    topic = _get_topic_or_404(db, topic_id)

    tier_sections = []
    for tier in DIFFICULTY_TIERS:
        try:
            questions = cache_service.get_questions(db, topic_id, tier)
        except cache_service.TopicNotFoundError:
            raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
        except AIGenerationError as exc:
            raise HTTPException(status_code=503, detail=f"{tier}: {exc}")

        cards = "".join(_question_card_html(q) for q in questions)
        tier_sections.append(
            f"""<div class="tier-section">
                  <h2><span class="tier-badge tier-{tier}">{tier}</span></h2>
                  {cards}
                </div>"""
        )

    body = _topic_header_html(topic) + "".join(tier_sections)
    pdf_bytes = _render_pdf(body)
    filename = f"questions-{topic.id}-{_slugify(topic.topic_name)}.pdf"
    return _pdf_response(pdf_bytes, filename)
