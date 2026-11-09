import argparse
from pathlib import Path

from .benchmark import evaluate, generate_benchmark, read_benchmark, write_evaluation
from .events import generate_events
from .process import analyze, read_event_log, write_analysis
from .scorecard import write_scorecard
from .triage import MockLLM, Triage


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore synthetic logistics automation")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="Generate a synthetic event log")
    generate.add_argument("--count", type=int, default=3000)
    generate.add_argument("--seed", type=int, default=2829)
    generate.add_argument("--output", type=Path, required=True)

    process = commands.add_parser("analyze", help="Analyze the CSV process log")
    process.add_argument("--events", type=Path, required=True)
    process.add_argument("--out", type=Path, required=True)

    rank = commands.add_parser("rank", help="Rank the candidate automation ideas")
    rank.add_argument("--cases", type=Path, default=Path("config/use-cases.yml"))
    rank.add_argument("--output", type=Path, default=Path("docs/use-cases.md"))

    benchmark = commands.add_parser("make-benchmark", help="Generate the labeled synthetic set")
    benchmark.add_argument("--scenarios", type=Path, default=Path("fixtures/triage-scenarios.yml"))
    benchmark.add_argument("--seed", type=int, default=2829)
    benchmark.add_argument("--output", type=Path, required=True)

    evaluation = commands.add_parser("evaluate", help="Score the deterministic mock")
    evaluation.add_argument("--cases", type=Path, default=Path("fixtures/triage-benchmark.csv"))
    evaluation.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate_events(args.output, args.count, args.seed)
            print(f"Generated {args.count} synthetic requests at {args.output}")
        elif args.command == "analyze":
            result = analyze(read_event_log(args.events))
            write_analysis(args.out, result)
            print(f"Analyzed {result.summary.requests} requests at {args.out}")
        elif args.command == "rank":
            write_scorecard(args.cases, args.output)
            print(f"Wrote use case scorecard at {args.output}")
        elif args.command == "make-benchmark":
            generate_benchmark(args.scenarios, args.output, args.seed)
            print(f"Wrote synthetic benchmark at {args.output}")
        else:
            result = evaluate(read_benchmark(args.cases), Triage(MockLLM()))
            write_evaluation(args.out, result)
            print(f"Mock accuracy {result.accuracy_pct:.2f}% ({result.correct}/{result.total}), "
                  f"{len(result.failures)} errors, {result.unflagged_errors} unflagged")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0
