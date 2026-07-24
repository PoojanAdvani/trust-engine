"""Entry point for `python -m trust_engine`.

Runs a small demo evaluation so the engine can be exercised end-to-end.
"""

from trust_engine import (
    AccountHistory,
    ClaimDetails,
    RiskFlags,
    TrustEngine,
    TrustSubject,
    __version__,
)


def main() -> None:
    print(f"Trust Engine v{__version__}\n")

    subject = TrustSubject(
        account=AccountHistory(
            account_age_days=420,
            verified_email=True,
            verified_phone=True,
            prior_claims=3,
            prior_disputes=0,
        ),
        claim=ClaimDetails(
            amount=1_200.0,
            has_documentation=True,
            days_since_incident=5,
        ),
        risk=RiskFlags(flags={"ip_mismatch": 0.3}),
    )

    result = TrustEngine().score(subject)
    print(result.explain())


if __name__ == "__main__":
    main()
