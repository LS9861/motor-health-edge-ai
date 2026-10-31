// src/inference/include/norm_params.h

#ifndef NORM_PARAMS_H
#define NORM_PARAMS_H

// Generated from data/processed/train_mean.npy and train_std.npy
// Channels: [ax, ay, az, current_mA, voltage_v, rpm]

static const float NORM_MEAN[6] = {
    -0.8520f,   // ax
     0.1577f,   // ay
    10.5465f,   // az
   114.8340f,  // current_mA
     5.9893f,   // voltage_v
   177.0138f   // rpm
};

static const float NORM_STD[6] = {
    0.1823f,   // ax
    0.4800f,   // ay
    0.3332f,   // az
   75.6060f,   // current_mA
    0.0251f,   // voltage_v
  152.3184f    // rpm
};

#endif