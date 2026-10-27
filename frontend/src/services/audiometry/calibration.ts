/**
 * Audiometric Calibration & Device Profile Layer
 *
 * Provides abstraction for transducer profiles, device characteristics,
 * and software stimulus levels.
 *
 * NOTE: This application is a screening/research prototype.
 * Software stimulus levels must NOT be claimed as certified clinical dB HL
 * unless a laboratory-calibrated coupler and validated transducer are present.
 */

export interface CalibrationProfile {
  profileId: string;
  deviceType: string;
  headphoneType: string;
  referenceSystemVolume: number; // e.g. 0.50 (50% system volume)
  isSystemVolumeLocked: boolean;
  frequencyCorrectionFactors: { [freq: number]: number };
  calibrationStatus: 'Uncalibrated Consumer Hardware' | 'Estimated Profile' | 'Standard Reference';
  disclaimer: string;
  osVolumeNotice: string;
}

export const CLINICAL_SCREENING_DISCLAIMER =
  'This application is a preliminary hearing screening prototype. Software stimulus intensity levels ' +
  'are generated independently via browser Web Audio and are NOT equivalent to calibrated clinical dB HL. ' +
  'This screening does not replace a comprehensive diagnostic evaluation by a licensed audiologist or ENT physician.';

export const OS_VOLUME_FIXED_NOTICE =
  'Operating System Audio Notice: Standard web browser security sandboxes prohibit direct programmatic ' +
  'locking of your device master volume. Please manually set your device/media volume to 50% now and ' +
  'DO NOT adjust device buttons during the test. All stimulus intensity changes are handled internally in software.';

export function getCalibrationProfile(
  deviceType: string = 'Laptop',
  headphoneType: string = 'Over-ear headphones'
): CalibrationProfile {
  // Equal-loudness / headphone acoustic correction factors relative to 1000 Hz
  const factors: { [freq: number]: number } = {
    250: 1.15,
    500: 1.05,
    1000: 1.00,
    2000: 0.95,
    4000: 0.90,
    8000: 1.10,
  };

  return {
    profileId: `cal-${deviceType.toLowerCase().replace(/\s+/g, '-')}-${headphoneType.toLowerCase().replace(/\s+/g, '-')}`,
    deviceType,
    headphoneType,
    referenceSystemVolume: 0.50,
    isSystemVolumeLocked: true, // Application assumes participant keeps OS volume constant
    frequencyCorrectionFactors: factors,
    calibrationStatus: 'Estimated Profile',
    disclaimer: CLINICAL_SCREENING_DISCLAIMER,
    osVolumeNotice: OS_VOLUME_FIXED_NOTICE,
  };
}
