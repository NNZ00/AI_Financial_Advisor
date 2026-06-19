"""Stage 6 — run the evaluation suite and log experiments to LangSmith.

    python run_eval.py              # full scorecard over the dataset
    python run_eval.py consistency  # the 'one fund' case x5, to measure stability
"""
import sys

from langsmith import Client, evaluate

from financial_advisor.evaluation import (
    EVAL_CASES, run_system,
    is_diversified, weights_sum_100, has_disclaimer, risk_fit_for_horizon, honesty_judge,
)

FULL_AGENT_DATASET_NAME = "trading-agent-eval"
CONSISTENCY_DATASET_NAME = "trading-agent-consistency"
EVALUATORS = [is_diversified, weights_sum_100, has_disclaimer, risk_fit_for_horizon, honesty_judge]


def _get_or_create(client: Client, name: str, cases: list) -> str:
    if client.has_dataset(dataset_name=name):
        print(f"Dataset '{name}' exists — reusing it.")
    else:
        print(f"Creating dataset '{name}' with {len(cases)} case(s).")
        client.create_dataset(dataset_name=name,
                              description="Investor requests for evaluating the trading-agent.")
        client.create_examples(dataset_name=name, examples=cases)
    return name


def run_full():
    client = Client()
    dataset = _get_or_create(client, FULL_AGENT_DATASET_NAME, EVAL_CASES)
    evaluate(
        run_system,
        data=dataset,
        evaluators=EVALUATORS,
        experiment_prefix="full",
        max_concurrency=1,   # sequential: avoids tool rate-limits and yfinance threading
    )
    print("Done — open the experiment in LangSmith for the scorecard.")


def run_consistency(reps: int = 5):
    client = Client()
    one_fund = [c for c in EVAL_CASES if c["metadata"]["case"] == "one_fund_simplicity"]
    dataset = _get_or_create(client, CONSISTENCY_DATASET_NAME, one_fund)
    evaluate(
        run_system,
        data=dataset,
        evaluators=[is_diversified, risk_fit_for_horizon],
        experiment_prefix="consistency",
        num_repetitions=reps,
        max_concurrency=1,
    )
    print(f"Ran the one-fund case {reps}x. In LangSmith, is_diversified should read 1.00 "
          "across every repetition if the bright-line fix holds.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "consistency":
        run_consistency()
    else:
        run_full()