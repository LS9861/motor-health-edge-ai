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
    -2.017085f,  // ax
    0.693677f,  // ay
    10.399394f,  // az
    189.819397f,  // current_mA
    265.271576f,  // rpm
};

static const float NORM_STD[5] = {
    0.317312f,  // ax
    0.304481f,  // ay
    0.258245f,  // az
    88.526390f,  // current_mA
    12.894553f,  // rpm
};

#endif  // NORM_PARAMS_H
