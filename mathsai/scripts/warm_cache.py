#!/usr/bin/env python3
"""Pre-generate lesson and question content so it is cached before you need it.

Generation takes ~2.5 minutes per lesson and ~45s per question tier. That is
fine the evening before, and not fine five minutes before a lesson — so this walks the
topics you choose and asks the server to generate each one now.

It drives the LIVE API over HTTP rather than writing to a database directly.
That is deliberate: the deployed instance keeps its SQLite file on its own
disk, so a script writing to a local database would populate the wrong copy
and appear to do nothing.

Already-cached content is skipped for free — `has_cached_lesson` on the topics
list and the questions `status` endpoint both report state without triggering
generation — so re-running after an interruption costs nothing for what is
already done.

Usage
-----
    export MATHSAI_URL=https://your-instance.onrender.com
    export MATHSAI_PASSWORD='...'

    python scripts/warm_cache.py --dry-run                # show the plan, spend nothing
    python scripts/warm_cache.py --key-stage KS3 --strand Algebra
    python scripts/warm_cache.py --topics 15 26 41
    python scripts/warm_cache.py --all --lessons-only
"""

import argparse
import os
import sys
import time
from typing import Optional

try:
    import httpx
except ImportError:  # pragma: no cover - dependency hint only
    sys.exit("httpx is required:  pip install httpx")

TIERS = ("Fluency", "Reasoning", "Problem-solving")

# Rough figures for the estimate only — actual cost depends on the topic.
# Measured on Opus 5 at effort=high with adaptive thinking: one lesson is
# three concurrent calls totalling ~4.3k input / ~27.7k output tokens, about
# $0.71. Thinking tokens bill as output, which is most of the difference from
# Sonnet. Update these if MODEL or EFFORT changes in ai_service.py.
COST_PER_LESSON_GBP = 0.56
COST_PER_TIER_GBP = 0.08
SECONDS_PER_LESSON = 150
SECONDS_PER_TIER = 45


class Client:
    def __init__(self, base_url: str, password: str, timeout: float = 300.0):
        self.base = base_url.rstrip("/")
        # Long timeout: a lesson is three concurrent model calls and the
        # request genuinely stays open for ~40s.
        self.http = httpx.Client(timeout=timeout, follow_redirects=False)
        self._login(password)

    def _login(self, password: str) -> None:
        response = self.http.post(
            f"{self.base}/api/auth/login", json={"password": password}
        )
        if response.status_code != 200:
            sys.exit(
                f"Login failed ({response.status_code}). Check MATHSAI_PASSWORD."
            )

    def topics(self) -> list:
        response = self.http.get(f"{self.base}/api/topics")
        response.raise_for_status()
        return response.json()

    def questions_cached(self, topic_id: int, tier: str) -> bool:
        """Never triggers generation — the status route exists for exactly this."""
        response = self.http.get(
            f"{self.base}/api/questions/{topic_id}/{tier}/status"
        )
        if response.status_code != 200:
            return False
        body = response.json()
        return bool(body) and body.get("generated_at") is not None

    def generate_lesson(self, topic_id: int) -> None:
        self.http.get(f"{self.base}/api/lessons/{topic_id}").raise_for_status()

    def generate_questions(self, topic_id: int, tier: str) -> None:
        self.http.get(
            f"{self.base}/api/questions/{topic_id}/{tier}"
        ).raise_for_status()


def select_topics(topics: list, args) -> list:
    if args.topics:
        wanted = set(args.topics)
        return [t for t in topics if t["id"] in wanted]
    chosen = topics
    if args.key_stage:
        chosen = [t for t in chosen if t["key_stage"].upper() == args.key_stage.upper()]
    if args.strand:
        needle = args.strand.lower()
        chosen = [t for t in chosen if needle in t["strand"].lower()]
    return chosen


def build_plan(client: Client, topics: list, lessons_only: bool) -> list:
    """Work out what is actually missing. Costs nothing to compute."""
    plan = []
    for topic in topics:
        work = []
        if not topic.get("has_cached_lesson"):
            work.append("lesson")
        if not lessons_only:
            work.extend(
                tier for tier in TIERS if not client.questions_cached(topic["id"], tier)
            )
        if work:
            plan.append((topic, work))
    return plan


def estimate(plan: list) -> float:
    return sum(
        COST_PER_LESSON_GBP if item == "lesson" else COST_PER_TIER_GBP
        for _, work in plan
        for item in work
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("MATHSAI_URL"))
    parser.add_argument("--password", default=os.getenv("MATHSAI_PASSWORD"))
    parser.add_argument("--key-stage", help="KS3 or KS4")
    parser.add_argument("--strand", help="substring match, e.g. Algebra")
    parser.add_argument("--topics", nargs="*", type=int, help="explicit topic ids")
    parser.add_argument("--all", action="store_true", help="every topic")
    parser.add_argument("--lessons-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="plan only, spend nothing")
    parser.add_argument("--pause", type=float, default=1.0, help="seconds between calls")
    args = parser.parse_args()

    if not args.url or not args.password:
        return parser.error("set MATHSAI_URL and MATHSAI_PASSWORD (or --url/--password)")
    if not any([args.all, args.key_stage, args.strand, args.topics]):
        return parser.error(
            "choose a scope: --all, --key-stage, --strand or --topics. "
            "Warming all 74 topics takes several hours and costs around £60 "
            "on Opus 5, "
            "so it should be asked for explicitly."
        )

    client = Client(args.url, args.password)
    topics = select_topics(client.topics(), args)
    if not topics:
        print("No topics matched that filter.")
        return 0

    print(f"Checking what is already cached for {len(topics)} topic(s)…")
    plan = build_plan(client, topics, args.lessons_only)
    if not plan:
        print("Everything in scope is already cached. Nothing to do.")
        return 0

    units = sum(len(work) for _, work in plan)
    print(f"\n{units} item(s) to generate across {len(plan)} topic(s)")
    print(f"Estimated cost: about £{estimate(plan):.2f}")
    minutes = sum(
        SECONDS_PER_LESSON if item == "lesson" else SECONDS_PER_TIER
        for _, work in plan
        for item in work
    ) / 60
    print(f"Estimated time: about {minutes:.0f} minutes\n")
    for topic, work in plan:
        print(f"  {topic['id']:>3}  {topic['topic_name'][:46]:<46} {', '.join(work)}")

    if args.dry_run:
        print("\nDry run — nothing generated, nothing spent.")
        return 0

    if input("\nGenerate these now? [y/N] ").strip().lower() != "y":
        print("Cancelled.")
        return 0

    done = failed = 0
    started = time.monotonic()
    for topic, work in plan:
        for item in work:
            label = f"{topic['topic_name'][:40]} · {item}"
            print(f"  {label:<52}", end="", flush=True)
            try:
                if item == "lesson":
                    client.generate_lesson(topic["id"])
                else:
                    client.generate_questions(topic["id"], item)
                done += 1
                print("ok")
            except Exception as exc:  # noqa: BLE001 - report and keep going
                failed += 1
                print(f"FAILED ({type(exc).__name__})")
            time.sleep(args.pause)

    print(
        f"\nGenerated {done} item(s) in {(time.monotonic() - started) / 60:.1f} minutes"
        + (f", {failed} failed — re-run to retry just those." if failed else ".")
    )
    print("All new content is unreviewed: check it before classroom use.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
