"""Editorial segmentation benchmark module."""

from benchmarks.editorial_segmentation.runner import run_segmentation_benchmark
from benchmarks.editorial_segmentation.test_data import (
    SEGMENTATION_TEST_CASES,
    SegmentationTestCase,
)

__all__ = [
    "run_segmentation_benchmark",
    "SegmentationTestCase",
    "SEGMENTATION_TEST_CASES",
]
