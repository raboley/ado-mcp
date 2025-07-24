"""State validation functionality for work item operations."""

import logging

logger = logging.getLogger(__name__)


class StateValidator:
    """Validator for work item state transitions."""

    @staticmethod
    def validate_state_transition(
        project_id: str, work_item_type: str, from_state: str, to_state: str
    ) -> bool:
        """
        Validate that a state transition is allowed for a work item type.

        This method uses the detailed work item type information including
        state transition rules to validate whether a state change is allowed.

        Args:
            project_id: The project ID
            work_item_type: The work item type name
            from_state: The current state
            to_state: The target state

        Returns:
            True if the transition is allowed, False otherwise
        """
        try:
            from ado.client_container import get_ado_client
            from ado.work_items.client import WorkItemsClient

            # If states are the same, always allow (no transition)
            if from_state == to_state:
                logger.debug(
                    f"State transition validation: {from_state} -> {to_state} (no change, allowed)"
                )
                return True

            # Get the ADO client
            ado_client = get_ado_client()
            if not ado_client:
                logger.warning(
                    "ADO client not available for state transition validation, allowing transition"
                )
                return True

            work_items_client = WorkItemsClient(ado_client)

            # Get detailed work item type information including transitions
            try:
                work_item_type_details = work_items_client.get_work_item_type(
                    project_id, work_item_type
                )
            except Exception as e:
                logger.warning(
                    f"Failed to get work item type details for transition validation: {e}, allowing transition"
                )
                return True

            # Check if we have transition information
            if (
                not hasattr(work_item_type_details, "transitions")
                or not work_item_type_details.transitions
            ):
                logger.debug(
                    f"No transition information available for {work_item_type}, allowing transition"
                )
                return True

            transitions = work_item_type_details.transitions

            # Azure DevOps transitions are organized by from_state
            # Each from_state has a list of possible transitions
            if from_state not in transitions:
                logger.debug(
                    f"No transitions defined from state '{from_state}' for {work_item_type}, allowing transition"
                )
                return True

            from_state_transitions = transitions[from_state]
            if not isinstance(from_state_transitions, list):
                logger.debug(
                    f"Invalid transition format for state '{from_state}', allowing transition"
                )
                return True

            # Check if any transition allows moving to the target state
            for transition in from_state_transitions:
                if isinstance(transition, dict) and transition.get("to") == to_state:
                    logger.debug(
                        f"State transition validation: {from_state} -> {to_state} (allowed)"
                    )
                    return True

            # No valid transition found
            logger.info(
                f"State transition validation: {from_state} -> {to_state} (not allowed for {work_item_type})"
            )
            return False

        except Exception as e:
            logger.error(
                f"Error during state transition validation: {e}, allowing transition as fallback"
            )
            # In case of error, allow the transition to avoid breaking workflows
            return True
