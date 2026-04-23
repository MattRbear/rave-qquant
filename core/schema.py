from dataclasses import dataclass

@dataclass
class FeatureVector:
    wick_to_body_ratio: float
    spread_bps: float
    close_position: float
    depth_imbalance: float

    def validate(self) -> bool:
        """Basic sanity checks."""
        # Check for required fields
        assert self.wick_to_body_ratio >= 0, "wick_to_body_ratio must be >= 0"
        assert self.spread_bps >= 0, "spread_bps must be >= 0"
        assert 0 <= self.close_position <= 1, "close_position must be in [0, 1]"
        assert -1 <= self.depth_imbalance <= 1, "depth_imbalance must be in [-1, 1]"
        return True
