# -*- coding: utf-8 -*-
"""
Chapter 5: ERG-Specific Filtering

This module contains all filter implementations for ERG signal processing:
- Butterworth bandpass filter (ISCEV 0.3-300 Hz, 4th order)
- Notch filter for power-line interference (50/60 Hz)
- Median filter for spike removal
- Complete filter pipeline combining all three
"""

from .butterworth_bandpass import (
    design_butterworth_bandpass,
    apply_bandpass_filter,
    plot_filter_response
)

from .notch_filter import (
    design_notch_filter,
    apply_notch_filter,
    detect_mains_interference,
    plot_notch_response
)

from .median_filter import (
    apply_median_filter,
    create_test_signal_with_spike,
    visualize_median_filter_effect
)

from .complete_filter_pipeline import (
    apply_erg_filter_pipeline,
    plot_before_after
)

__all__ = [
    # Butterworth
    'design_butterworth_bandpass',
    'apply_bandpass_filter',
    'plot_filter_response',
    # Notch
    'design_notch_filter',
    'apply_notch_filter',
    'detect_mains_interference',
    'plot_notch_response',
    # Median
    'apply_median_filter',
    'create_test_signal_with_spike',
    'visualize_median_filter_effect',
    # Pipeline
    'apply_erg_filter_pipeline',
    'plot_before_after'
]
