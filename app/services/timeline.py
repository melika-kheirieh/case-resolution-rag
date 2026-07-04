from app.domain.models import TimelineEvent


def build_timeline(events: list[TimelineEvent]) -> list[TimelineEvent]:
    return sorted(events, key=lambda event: event.happened_at)
