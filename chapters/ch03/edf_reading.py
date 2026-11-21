# Chapter 3, §3.4.3: read the sample EDF file with MNE-Python
# Run from the repository folder:  python chapters/ch03/edf_reading.py
# This is the code of §3.4.3, reading the copy of patient_001.edf in
# data/samples/ instead of downloading it.

# Reading an EDF file with MNE-Python
# MNE returns EDF data in volts, using the unit stored in the file header.
# If amplitudes look 1,000 times too large or too small, check that header.
import mne
# Load the EDF file (verbose=False suppresses the MNE console output)
raw = mne.io.read_raw_edf('data/samples/patient_001.edf', preload=True, verbose=False)

# Extract the ERG channel by name
erg_data = raw.get_data(picks='ERG')[0]
times = raw.times

# erg_data is a NumPy array of voltage values in volts; convert to µV
erg_uV = erg_data * 1e6   # 1 volt = 1,000,000 microvolts

# times is a NumPy array of time points in seconds; convert to ms
times_ms = times * 1000

# Print a summary
print(f'Loaded {len(erg_uV)} samples at {raw.info["sfreq"]} Hz')
print(f'Duration: {times_ms[-1]:.1f} ms  |  Amplitude range: {erg_uV.min():.1f} to {erg_uV.max():.1f} µV')
