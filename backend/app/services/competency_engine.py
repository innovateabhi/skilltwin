def clamp_score(score: int | float) -> int:
    return max(0, min(100, round(score)))


def calculate_gap(
    current_score: int | float,
    target_score: int | float,
) -> int:
    current = clamp_score(current_score)
    target = clamp_score(target_score)

    return max(target - current, 0)


def calculate_severity(gap_score: int) -> str:
    if gap_score <= 0:
        return "none"

    if gap_score <= 15:
        return "low"

    if gap_score <= 30:
        return "moderate"

    return "critical"


def calculate_improvement(
    previous_score: int | float | None,
    current_score: int | float,
) -> int:
    current = clamp_score(current_score)

    if previous_score is None:
        return 0

    previous = clamp_score(previous_score)

    return current - previous