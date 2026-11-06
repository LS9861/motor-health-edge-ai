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
    -1.086705f,  // ax
    -0.004128f,  // ay
    10.497450f,  // az
    174.598969f,  // current_mA
    290.001923f,  // rpm
};

static const float NORM_STD[5] = {
    0.305561f,  // ax
    0.345472f,  // ay
    0.146230f,  // az
    68.693039f,  // current_mA
    9.909420f,  // rpm
};

#endif  // NORM_PARAMS_H
