"""Tests for timestamp utilities"""
import pytest
from datetime import datetime

from ecopower_tarrifs.domain.timestamp_utils import floor_to_15_minutes


class TestTimestampUtils:
    """Test suite for timestamp normalization"""

    def test_floor_to_15_minutes_exact_boundary(self):
        """Test flooring a timestamp that's already on a 15-minute boundary"""
        dt = datetime(2025, 10, 1, 12, 15, 0)
        result = floor_to_15_minutes(dt)
        assert result == datetime(2025, 10, 1, 12, 15, 0)

    def test_floor_to_15_minutes_with_seconds(self):
        """Test flooring removes seconds"""
        dt = datetime(2025, 10, 1, 12, 15, 42)
        result = floor_to_15_minutes(dt)
        assert result == datetime(2025, 10, 1, 12, 15, 0)

    def test_floor_to_15_minutes_with_microseconds(self):
        """Test flooring removes microseconds"""
        dt = datetime(2025, 10, 1, 12, 15, 0, 123456)
        result = floor_to_15_minutes(dt)
        assert result == datetime(2025, 10, 1, 12, 15, 0)

    def test_floor_to_15_minutes_rounds_down(self):
        """Test that timestamps between boundaries floor down"""
        test_cases = [
            (datetime(2025, 10, 1, 12, 7, 23), datetime(2025, 10, 1, 12, 0, 0)),
            (datetime(2025, 10, 1, 12, 16, 42), datetime(2025, 10, 1, 12, 15, 0)),
            (datetime(2025, 10, 1, 12, 29, 59), datetime(2025, 10, 1, 12, 15, 0)),
            (datetime(2025, 10, 1, 12, 47, 59), datetime(2025, 10, 1, 12, 45, 0)),
        ]

        for input_dt, expected_dt in test_cases:
            result = floor_to_15_minutes(input_dt)
            assert result == expected_dt, f"Failed for {input_dt}"

    def test_floor_to_15_minutes_all_quarters(self):
        """Test all four 15-minute quarters in an hour"""
        quarters = [
            (datetime(2025, 10, 1, 12, 0, 0), datetime(2025, 10, 1, 12, 0, 0)),
            (datetime(2025, 10, 1, 12, 15, 0), datetime(2025, 10, 1, 12, 15, 0)),
            (datetime(2025, 10, 1, 12, 30, 0), datetime(2025, 10, 1, 12, 30, 0)),
            (datetime(2025, 10, 1, 12, 45, 0), datetime(2025, 10, 1, 12, 45, 0)),
        ]

        for input_dt, expected_dt in quarters:
            result = floor_to_15_minutes(input_dt)
            assert result == expected_dt

    def test_floor_to_15_minutes_removes_timezone(self):
        """Test that timezone information is removed"""
        from datetime import timezone
        dt = datetime(2025, 10, 1, 12, 7, 23, tzinfo=timezone.utc)
        result = floor_to_15_minutes(dt)
        assert result.tzinfo is None
        assert result == datetime(2025, 10, 1, 12, 0, 0)

    def test_floor_to_15_minutes_midnight(self):
        """Test flooring near midnight"""
        dt = datetime(2025, 10, 2, 0, 0, 0)
        result = floor_to_15_minutes(dt)
        assert result == datetime(2025, 10, 2, 0, 0, 0)

    def test_floor_to_15_minutes_end_of_day(self):
        """Test flooring near end of day"""
        dt = datetime(2025, 10, 1, 23, 47, 59)
        result = floor_to_15_minutes(dt)
        assert result == datetime(2025, 10, 1, 23, 45, 0)
