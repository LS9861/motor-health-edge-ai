// src/inference/include/norm_params.h
//
// Auto-generated. DO NOT EDIT. Regenerate with:
//   python scripts/generate_norm_params.py
//
// Source: data/processed/train_mean.npy, train_std.npy
// Channels: [ax, ay, az, current_mA, rpm]  (voltage intentionally excluded)

#ifndef NORM_PARAMS_H
#define NORM_PARAMS_H

static const float NORM_MEAN[5] = {
    -1.074541f,  // ax
    0.003995f,  // ay
    10.499016f,  // az
    175.428467f,  // current_mA
    268.875366f,  // rpm
};

static const float NORM_STD[5] = {
    0.275936f,  // ax
    0.311171f,  // ay
    0.900699f,  // az
    85.365959f,  // current_mA
    24.758251f,  // rpm
};

#endif  // NORM_PARAMS_H
