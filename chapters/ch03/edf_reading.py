# Reading an EDF file with MNE-Python
# Verify the unit field in raw.info['chs'][0]['unit'] before scaling — some devices export in mV (multiply by 1e3) or µV (no scaling needed).

import mne

# Load the EDF file (verbose=False suppresses the MNE console output)
raw = mne.io.read_raw_edf('patient_001.edf', preload=True, verbose=False)

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