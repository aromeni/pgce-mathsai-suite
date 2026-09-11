/**
 * Renders the lesson components against a real API payload.
 *
 * Exists because a dangling variable reference in a component compiles
 * cleanly and only throws at runtime — which is exactly how a blank Lesson
 * page reached production. A build that succeeds proves nothing; this
 * actually executes the components.
 */
import { renderToString } from "react-dom/server";
import lesson from "./lesson.json";
import TeachingSequence from "../src/components/TeachingSequence.jsx";
import AdaptivePanel from "../src/components/AdaptivePanel.jsx";
import ReferencePanel from "../src/components/ReferencePanel.jsx";
import LessonActions from "../src/components/LessonActions.jsx";
import QuestionBlock from "../src/components/QuestionBlock.jsx";
import LegacyLessonPanel from "../src/components/LegacyLessonPanel.jsx";
import OutdatedFormatNotice from "../src/components/OutdatedFormatNotice.jsx";

const noop = () => {};
const question = {
  question_number: 1, type: "multiple_choice", question_text: "Work out 3(x+2)",
  options: ["A) 3x+2", "B) 3x+6"], answer: "3x+6", mark_scheme: "M1 oe; A1 cao",
  marks: 2, command_word: "Work out", calculator_allowed: false,
  misconception_targeted: "multiplies only the first term",
  requires_diagram: true, diagram_description: "A rectangle labelled x and 2.",
};
const legacy = { lesson_notes: "# Old", worked_examples: [], key_vocabulary: [], common_errors: [] };

const cases = {
  TeachingSequence: <TeachingSequence lesson={lesson} onGoToQuestions={noop} />,
  AdaptivePanel: <AdaptivePanel adaptive={lesson.adaptive_teaching} />,
  ReferencePanel: <ReferencePanel lesson={lesson} />,
  LessonActions: (
    <LessonActions topicId={1} navigate={noop} regenerating={false} onRegenerate={noop}
      exporting={false} onExportPdf={noop} taughtFormOpen taughtJustLogged={false}
      setTaughtFormOpen={noop} onTaughtLogged={noop} />
  ),
  QuestionBlock: <QuestionBlock question={question} />,
  LegacyLessonPanel: <LegacyLessonPanel lesson={legacy} />,
  OutdatedFormatNotice: <OutdatedFormatNotice onRegenerate={noop} busy={false} />,
};

let failed = 0;
for (const [name, element] of Object.entries(cases)) {
  try {
    const html = renderToString(element);
    console.log(`  OK      ${name.padEnd(22)} ${html.length} chars`);
  } catch (err) {
    failed++;
    console.log(`  CRASHED ${name.padEnd(22)} ${err.message}`);
  }
}
console.log(failed ? `\n${failed} component(s) crashed` : "\nAll components rendered.");
process.exit(failed ? 1 : 0);
