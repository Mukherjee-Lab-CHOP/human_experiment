"""Core probability-choice experiment logic, independent of the GUI."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Optional


HORIZONTAL = "HORIZONTAL"
VERTICAL = "VERTICAL"


@dataclass(frozen=True)
class Trial:
    number: int
    block: int
    reversed: bool
    left: str
    right: str
    horizontal_probability: float
    vertical_probability: float
    horizontal_unchosen: int
    vertical_unchosen: int
    horizontal_baited: bool
    vertical_baited: bool


@dataclass(frozen=True)
class Result:
    choice: Optional[str]
    side: str
    rewarded: bool
    points: int


class ProbabilityReversalExperiment:
    """Independently baited H/V task with optional fixed-length reversals.

    Reward baiting matches Shrew-HVScreen's ``choose_orientation`` task:
    ``1 - (1 - base_probability) ** (unchosen_count + 1)``. Once baited, an
    option remains rewarded until selected. A reversal starts a fresh block,
    swaps the two base probabilities, and clears bait/counter state.
    """

    def __init__(
        self,
        high_probability: float = 0.8,
        low_probability: float = 0.2,
        reversal_every: int = 40,
        seed: Optional[int] = None,
    ) -> None:
        if not 0 <= low_probability <= high_probability <= 1:
            raise ValueError("Probabilities must satisfy 0 <= low <= high <= 1")
        if reversal_every < 0:
            raise ValueError("reversal_every cannot be negative")
        self.high_probability = high_probability
        self.low_probability = low_probability
        self.reversal_every = reversal_every
        self.rng = random.Random(seed)
        self.completed = 0
        self.horizontal_unchosen = 0
        self.vertical_unchosen = 0
        self.horizontal_baited = False
        self.vertical_baited = False
        self.current_trial: Optional[Trial] = None

    @property
    def block(self) -> int:
        if not self.reversal_every:
            return 1
        return (self.completed // self.reversal_every) + 1

    @property
    def reversed(self) -> bool:
        return self.block % 2 == 0

    def _base_probabilities(self) -> tuple[float, float]:
        if self.reversed:
            return self.low_probability, self.high_probability
        return self.high_probability, self.low_probability

    @staticmethod
    def effective_probability(base: float, unchosen: int) -> float:
        return 1.0 - ((1.0 - base) ** (unchosen + 1))

    def start_trial(self) -> Trial:
        if self.current_trial is not None:
            raise RuntimeError("The current trial must be completed first")

        h_probability, v_probability = self._base_probabilities()
        if not self.horizontal_baited:
            chance = self.effective_probability(
                h_probability, self.horizontal_unchosen
            )
            self.horizontal_baited = self.rng.random() < chance
        if not self.vertical_baited:
            chance = self.effective_probability(v_probability, self.vertical_unchosen)
            self.vertical_baited = self.rng.random() < chance

        if self.rng.randint(0, 1) == 0:
            left, right = HORIZONTAL, VERTICAL
        else:
            left, right = VERTICAL, HORIZONTAL

        self.current_trial = Trial(
            number=self.completed + 1,
            block=self.block,
            reversed=self.reversed,
            left=left,
            right=right,
            horizontal_probability=h_probability,
            vertical_probability=v_probability,
            horizontal_unchosen=self.horizontal_unchosen,
            vertical_unchosen=self.vertical_unchosen,
            horizontal_baited=self.horizontal_baited,
            vertical_baited=self.vertical_baited,
        )
        return self.current_trial

    def choose(self, side: str) -> Result:
        if self.current_trial is None:
            raise RuntimeError("No trial is active")
        if side not in ("LEFT", "RIGHT"):
            raise ValueError("side must be LEFT or RIGHT")

        choice = self.current_trial.left if side == "LEFT" else self.current_trial.right
        rewarded = (
            self.horizontal_baited if choice == HORIZONTAL else self.vertical_baited
        )
        if rewarded:
            if choice == HORIZONTAL:
                self.horizontal_baited = False
            else:
                self.vertical_baited = False

        if choice == HORIZONTAL:
            self.horizontal_unchosen = 0
            self.vertical_unchosen += 1
        else:
            self.vertical_unchosen = 0
            self.horizontal_unchosen += 1

        old_block = self.block
        self.completed += 1
        if self.block != old_block:
            # A new reversal block is a clean condition, not inherited bait.
            self.horizontal_unchosen = 0
            self.vertical_unchosen = 0
            self.horizontal_baited = False
            self.vertical_baited = False

        self.current_trial = None
        return Result(choice=choice, side=side, rewarded=rewarded, points=int(rewarded))

    def timeout(self) -> Result:
        """End without a choice; counters and existing bait remain unchanged."""
        if self.current_trial is None:
            raise RuntimeError("No trial is active")
        old_block = self.block
        self.completed += 1
        if self.block != old_block:
            self.horizontal_unchosen = 0
            self.vertical_unchosen = 0
            self.horizontal_baited = False
            self.vertical_baited = False
        self.current_trial = None
        return Result(choice=None, side="TIMEOUT", rewarded=False, points=0)
