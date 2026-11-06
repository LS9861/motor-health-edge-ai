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
    -1.084395f,  // ax
    -0.000128f,  // ay
    10.496672f,  // az
    163.251129f,  // current_mA
    284.287750f,  // rpm
};

static const float NORM_STD[5] = {
    0.273534f,  // ax
    0.354653f,  // ay
    0.144241f,  // az
    64.454613f,  // current_mA
    17.618126f,  // rpm
};

#endif  // NORM_PARAMS_H
