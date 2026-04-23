import pytest
from core.schema import FeatureVector

def test_feature_vector_valid():
    """Test valid FeatureVector parameters."""
    fv = FeatureVector(
        wick_to_body_ratio=1.5,
        spread_bps=2.0,
        close_position=0.5,
        depth_imbalance=0.1
    )
    assert fv.validate() is True

def test_feature_vector_wick_ratio_negative():
    """Test wick_to_body_ratio < 0 raises AssertionError."""
    fv = FeatureVector(-0.1, 2.0, 0.5, 0.1)
    with pytest.raises(AssertionError, match="wick_to_body_ratio must be >= 0"):
        fv.validate()

def test_feature_vector_spread_bps_negative():
    """Test spread_bps < 0 raises AssertionError."""
    fv = FeatureVector(1.5, -0.1, 0.5, 0.1)
    with pytest.raises(AssertionError, match="spread_bps must be >= 0"):
        fv.validate()

def test_feature_vector_close_position_below_zero():
    """Test close_position < 0 raises AssertionError."""
    fv = FeatureVector(1.5, 2.0, -0.1, 0.1)
    with pytest.raises(AssertionError, match=r"close_position must be in \[0, 1\]"):
        fv.validate()

def test_feature_vector_close_position_above_one():
    """Test close_position > 1 raises AssertionError."""
    fv = FeatureVector(1.5, 2.0, 1.1, 0.1)
    with pytest.raises(AssertionError, match=r"close_position must be in \[0, 1\]"):
        fv.validate()

def test_feature_vector_depth_imbalance_below_minus_one():
    """Test depth_imbalance < -1 raises AssertionError."""
    fv = FeatureVector(1.5, 2.0, 0.5, -1.1)
    with pytest.raises(AssertionError, match=r"depth_imbalance must be in \[-1, 1\]"):
        fv.validate()

def test_feature_vector_depth_imbalance_above_one():
    """Test depth_imbalance > 1 raises AssertionError."""
    fv = FeatureVector(1.5, 2.0, 0.5, 1.1)
    with pytest.raises(AssertionError, match=r"depth_imbalance must be in \[-1, 1\]"):
        fv.validate()

def test_feature_vector_edge_cases():
    """Test boundary edge cases for FeatureVector validation."""
    # wick_to_body_ratio boundary
    fv1 = FeatureVector(0.0, 2.0, 0.5, 0.1)
    assert fv1.validate() is True

    # spread_bps boundary
    fv2 = FeatureVector(1.5, 0.0, 0.5, 0.1)
    assert fv2.validate() is True

    # close_position boundaries
    fv3 = FeatureVector(1.5, 2.0, 0.0, 0.1)
    assert fv3.validate() is True
    fv4 = FeatureVector(1.5, 2.0, 1.0, 0.1)
    assert fv4.validate() is True

    # depth_imbalance boundaries
    fv5 = FeatureVector(1.5, 2.0, 0.5, -1.0)
    assert fv5.validate() is True
    fv6 = FeatureVector(1.5, 2.0, 0.5, 1.0)
    assert fv6.validate() is True
