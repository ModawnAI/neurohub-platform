"""Unit tests for the request state machine.

Tests validate:
- All valid transitions succeed
- Invalid transitions raise 422
- Terminal state transitions raise 409
- Role gating (only allowed roles can perform transitions)
- No-op transitions raise 422
"""

import pytest
from fastapi import HTTPException

from app.dependencies import CurrentUser
from app.services.state_machine import (
    TERMINAL_STATES,
    TRANSITIONS,
    RequestStatus,
    validate_transition,
)
from tests.conftest import DEFAULT_INSTITUTION_ID


def _user(roles: list[str]) -> CurrentUser:
    import uuid

    return CurrentUser(
        id=uuid.uuid4(),
        username="tester",
        institution_id=DEFAULT_INSTITUTION_ID,
        roles=roles,
    )


class TestValidTransitions:
    """Every defined transition should succeed when the actor has an allowed role."""

    @pytest.mark.parametrize(
        "from_s,to_s",
        list(TRANSITIONS.keys()),
    )
    def test_valid_transition_succeeds_with_allowed_role(self, from_s, to_s):
        allowed_roles = TRANSITIONS[(from_s, to_s)]
        user = _user(list(allowed_roles)[:1])
        # Should not raise
        validate_transition(from_s, to_s, user)

    def test_valid_transition_without_actor_succeeds(self):
        validate_transition(RequestStatus.CREATED, RequestStatus.RECEIVING, actor=None)


class TestInvalidTransitions:
    """Transitions not in the TRANSITIONS dict should raise 422."""

    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            (RequestStatus.CREATED, RequestStatus.COMPUTING),
            (RequestStatus.CREATED, RequestStatus.QC),
            (RequestStatus.RECEIVING, RequestStatus.COMPUTING),
            (RequestStatus.STAGING, RequestStatus.COMPUTING),
            (RequestStatus.QC, RequestStatus.STAGING),
            (RequestStatus.FINAL, RequestStatus.CREATED),
        ],
    )
    def test_invalid_transition_raises_422(self, from_s, to_s):
        user = _user(["SYSTEM_ADMIN"])
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(from_s, to_s, user)
        assert exc_info.value.status_code in (409, 422)


class TestTerminalStates:
    """No transition allowed from terminal states."""

    @pytest.mark.parametrize("terminal", list(TERMINAL_STATES))
    @pytest.mark.parametrize(
        "target",
        [RequestStatus.CREATED, RequestStatus.RECEIVING, RequestStatus.COMPUTING],
    )
    def test_transition_from_terminal_raises_409(self, terminal, target):
        user = _user(["SYSTEM_ADMIN"])
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(terminal, target, user)
        assert exc_info.value.status_code == 409


class TestRoleGating:
    """Users without the required role should get 403."""

    def test_physician_cannot_transition_computing_to_qc(self):
        user = _user(["PHYSICIAN"])
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(RequestStatus.COMPUTING, RequestStatus.QC, user)
        assert exc_info.value.status_code == 403

    def test_reviewer_cannot_cancel_request(self):
        user = _user(["REVIEWER"])
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(RequestStatus.CREATED, RequestStatus.CANCELLED, user)
        assert exc_info.value.status_code == 403

    def test_system_admin_can_do_everything_in_transitions(self):
        user = _user(["SYSTEM_ADMIN"])
        for (from_s, to_s), _ in TRANSITIONS.items():
            if "SYSTEM_ADMIN" in TRANSITIONS[(from_s, to_s)]:
                validate_transition(from_s, to_s, user)


class TestNoopTransition:
    """Same-state transition should raise 422."""

    @pytest.mark.parametrize("state", list(RequestStatus))
    def test_noop_raises_422(self, state):
        user = _user(["SYSTEM_ADMIN"])
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(state, state, user)
        assert exc_info.value.status_code == 422
