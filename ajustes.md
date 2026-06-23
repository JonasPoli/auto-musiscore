python musescore_strings_16part.py --midi "mid/002- De Deus tu és eleita.mid" --preset 9 --speed 0.9 --output output_strings_16part


python postprocess_fade_apos_pausa.py --input "output_strings_16part/002- De Deus tu és eleita_preset9_16part_speed90.mp3" --output "output_strings_16part" --suffix "_suave" --lookback-ms 200


