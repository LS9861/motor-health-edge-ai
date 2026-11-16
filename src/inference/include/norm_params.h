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
    -1.109278f,  // ax
    0.004202f,  // ay
    10.518171f,  // az
    195.544495f,  // current_mA
    270.588104f,  // rpm
};

static const float NORM_STD[5] = {
    0.349741f,  // ax
    0.308783f,  // ay
    0.910247f,  // az
    99.463188f,  // current_mA
    23.990839f,  // rpm
};

#endif  // NORM_PARAMS_H
