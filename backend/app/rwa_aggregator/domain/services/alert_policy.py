"""Alert policy domain service for alert trigger evaluation.

Implements F-003: Alert System rules from the MVP specification.
- F-003.3: Trigger when current_spread < threshold AND previous_spread >= threshold
- F-003.4: Enforce cooldown between alerts (delegated to Alert entity)
"""

from typing import Optional

from app.rwa_aggregator.domain.entities.alert import Alert
from app.rwa_aggregator.domain.value_objects.spread import Spread


class AlertPolicy:
    """Domain service for evaluating alert trigger conditions.

    This service implements pure domain logic with no infrastructure dependencies.
    It determines whether an alert should fire based on spread threshold crossing
    and the alert's eligibility state.

    The crossing behavior (F-003.3) ensures alerts only fire when the spread
    transitions from at-or-above the threshold to below it, preventing repeated
    triggers while spread remains low.
    """

    def should_trigger(
        self,
        alert: Alert,
        current_spread: Spread,
        previous_spread: Optional[Spread],
    ) -> bool:
        """Determine if an alert should trigger based on spread conditions.

        Rules:
        1. Alert must be eligible to trigger (active status + past cooldown)
        2. Current spread must be below the alert's threshold
        3. Previous spread must have been at or above threshold (crossing behavior)
           - If no previous spread exists, only check current is below threshold

        Args:
            alert: The alert configuration to evaluate.
            current_spread: The current effective spread.
            previous_spread: The previous effective spread, or None for first evaluation.

        Returns:
            True if the alert should trigger, False otherwise.
        """
        # Check alert eligibility (enforces active status + cooldown per F-003.4)
        if not alert.can_trigger():
            return False

        threshold = alert.threshold_pct

        # Check if current spread is below threshold
        is_below_now = current_spread.is_below_threshold(threshold)

        # First evaluation - no crossing check possible
        if previous_spread is None:
            return is_below_now

        # Crossing behavior per F-003.3:
        # Trigger only when crossing from above/at threshold to below
        was_at_or_above = not previous_spread.is_below_threshold(threshold)

        return is_below_now and was_at_or_above
