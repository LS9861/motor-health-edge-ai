#!/usr/bin/env python3
"""Generate ML_Guide_for_Motor_Health.pdf (self-contained, ReportLab only)."""

import os

HERE = os.path.dirname(os.path.abspath(__file__))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

ACCENT = colors.HexColor("#1f6feb")
ACCENT_DARK = colors.HexColor("#0b3d91")
LIGHT = colors.HexColor("#eef4ff")
GREY = colors.HexColor("#555555")
CODE_BG = colors.HexColor("#f3f4f6")
AMBER_BG = colors.HexColor("#fff7e6")

styles = getSampleStyleSheet()


def s(name, **kw):
    return ParagraphStyle(name, parent=styles["BodyText"], **kw)


TITLE = s("Title", fontName="Helvetica-Bold", fontSize=26, leading=32,
          textColor=ACCENT_DARK, alignment=TA_CENTER, spaceAfter=6)
SUBTITLE = s("Subtitle", fontName="Helvetica", fontSize=12.5, leading=17,
             textColor=GREY, alignment=TA_CENTER, spaceAfter=4)
H1 = s("H1", fontName="Helvetica-Bold", fontSize=16, leading=20,
       textColor=ACCENT_DARK, spaceBefore=14, spaceAfter=6)
H2 = s("H2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
       textColor=ACCENT, spaceBefore=10, spaceAfter=4)
BODY = s("Body", fontName="Helvetica", fontSize=10, leading=14.5,
         alignment=TA_JUSTIFY, spaceAfter=6)
BULLET = s("Bullet", fontName="Helvetica", fontSize=10, leading=14,
           alignment=TA_LEFT)
SMALL = s("Small", fontName="Helvetica-Oblique", fontSize=8.5, leading=11,
          textColor=GREY)
CALL = s("Call", fontName="Helvetica", fontSize=9.5, leading=13.5,
         textColor=colors.HexColor("#7a4a00"))
CALLH = s("CallH", fontName="Helvetica-Bold", fontSize=9.5, leading=13,
          textColor=colors.HexColor("#7a4a00"))
CODE = s("Code", fontName="Courier", fontSize=8.5, leading=11.5,
         textColor=colors.HexColor("#111111"))


def P(t, st=BODY):
    return Paragraph(t, st)


def bullets(items, st=BULLET):
    return ListFlowable(
        [ListItem(P(i, st), leftIndent=12, value="circle") for i in items],
        bulletType="bullet", start="\u2022", leftIndent=16, bulletFontSize=8,
        spaceBefore=2, spaceAfter=6,
    )


def callout(title, text):
    inner = [P("<b>%s</b>" % title, CALLH), P(text, CALL)]
    t = Table([[inner]], colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMBER_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e0a800")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def code_block(lines):
    esc = "<br/>".join(
        l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for l in lines
    )
    t = Table([[P(esc, CODE)]], colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d7de")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def table(data, col_widths, header=True, font_size=9):
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d1d9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 8)])


def hr():
    return HRFlowable(width="100%", thickness=0.8,
                      color=colors.HexColor("#c9d1d9"),
                      spaceBefore=4, spaceAfter=8)


story = []

# ---------------------------------------------------------------- COVER
story.append(Spacer(1, 38 * mm))
story.append(P("Motor Health Edge AI", TITLE))
story.append(P("A Practical Machine-Learning Guide", SUBTITLE))
story.append(P("How we built an ESP32 fault classifier from scratch \u2014 "
               "explained for beginners and engineers", SUBTITLE))
story.append(Spacer(1, 6 * mm))
story.append(HRFlowable(width="60%", thickness=1.2, color=ACCENT, hAlign="CENTER"))
story.append(Spacer(1, 6 * mm))
story.append(P("Project: <b>motor-health-edge-ai</b> &nbsp;|&nbsp; Target: "
               "ESP32-C3 + TensorFlow Lite Micro",
               s("cv", fontName="Helvetica", fontSize=10.5, leading=16,
                 textColor=ACCENT_DARK, alignment=TA_CENTER)))
story.append(P("Motor: JGA25-370 (built-in magnetic encoder, 12\u201314 V) "
               "&nbsp;|&nbsp; Sensors: MPU6050 + INA228 + encoder",
               s("cv2", fontName="Helvetica", fontSize=9.5, leading=15,
                 textColor=GREY, alignment=TA_CENTER)))
story.append(Spacer(1, 14 * mm))
story.append(callout(
    "Who is this for?",
    "Anyone curious about machine learning on tiny devices. Sections 1\u20134 "
    "explain the ideas in plain language (great for a first learner). "
    "Sections 5\u20138 go deeper into the engineering choices (architecture, "
    "training, deployment). The final section is a one-page project summary."))
story.append(PageBreak())

# Guide body A: TOC + sections 1-6.

# ---------------------------------------------------------------- TOC
story.append(P("What's inside", H1))
story.append(hr())
toc = [
    ("1", "What are we trying to do? (the aim)", "The problem, goal & success criteria"),
    ("2", "What is machine learning, really?", "Patterns from examples \u2014 the 30-second version"),
    ("3", "The data: what we measured and why", "5 signals, windowing, labels"),
    ("4", "The variables that matter most", "Feature selection, leakage, shortcut learning"),
    ("5", "Why a 1D CNN specifically?", "Architecture choice, trade-offs vs other models"),
    ("6", "The training method, step by step", "Loss, optimiser, augmentation, early stopping"),
    ("7", "The full ML pipeline", "Raw CSV \u2192 deployable model, end to end"),
    ("8", "Getting it onto a microcontroller", "INT8 quantisation, TFLM, latency, memory"),
    ("9", "Project summary", "Methods, results, lessons learned"),
]
rows = [["#", "Section", "In one line"]]
rows += [[r[0], P(r[1], BULLET), P(r[2], SMALL)] for r in toc]
story.append(table(rows, [10 * mm, 70 * mm, 85 * mm]))
story.append(Spacer(1, 3 * mm))
story.append(callout(
    "Results at a glance",
    "3 classes (healthy / imbalanced / friction) \u2022 5-channel 1D-CNN \u2022 "
    "963 parameters \u2022 ~5.6 KB model \u2022 100% test accuracy (117/117, INT8 "
    "lossless) \u2022 27.9 ms inference on ESP32-C3 @ 160 MHz \u2022 ~94% CPU "
    "headroom at 1 Hz."))
story.append(PageBreak())

# ---------------------------------------------------------------- 1
story.append(P("1. What are we trying to do?", H1))
story.append(hr())
story.append(P(
    "Electric motors are everywhere \u2014 fans, conveyor belts, pumps, robots. "
    "When a motor starts to fail, it usually does not stop suddenly. It gives "
    "warning signs: unusual vibration, extra current draw, a wobble or a rub. "
    "Our goal is to <b>detect those signs automatically, on the device itself</b>, "
    "so a cheap microcontroller can say \u201cthis motor needs attention\u201d "
    "without sending data to the cloud."))
story.append(P("Three health states to recognise:", H2))
story.append(bullets([
    "<b>Healthy</b> \u2014 the motor runs normally.",
    "<b>Imbalanced</b> \u2014 a small off-centre mass makes the shaft vibrate "
    "(like a washing machine with an uneven load).",
    "<b>Friction</b> \u2014 extra mechanical resistance slows the motor and pulls "
    "more current.",
]))
story.append(P("Why \u201con the edge\u201d?", H2))
story.append(P(
    "Running the model on the microcontroller (the \u201cedge\u201d) means instant "
    "decisions, no internet needed, no privacy concerns, and very low cost. The "
    "catch: the chip is tiny (about 400 KB of RAM, 4 MB flash, 160 MHz, no GPU). "
    "Every byte and every millisecond counts \u2014 and that single constraint "
    "shapes almost every machine-learning decision in this project."))
story.append(callout(
    "Aim & success criteria",
    "Goal: a model small enough for an ESP32-C3 that classifies motor health "
    "from live sensor data at 1 Hz, with high accuracy and low latency. "
    "Success = \u226590% accuracy on unseen data, model < 100 KB, inference "
    "well under the 1-second budget (we hit 27.9 ms)."))

# ---------------------------------------------------------------- 2
story.append(P("2. What is machine learning, really?", H1))
story.append(hr())
story.append(P(
    "Traditional programming is: <i>write rules \u2192 get answers</i>. Machine "
    "learning flips it: <i>give examples (inputs + correct answers) \u2192 the "
    "computer finds the rules</i>. Those discovered rules are stored in the "
    "model\u2019s <b>parameters</b> (numbers)."))
story.append(P("Two ideas you must know", H2))
story.append(bullets([
    "<b>Training</b> \u2014 showing the model thousands of labelled examples and "
    "nudging its numbers so its answers get closer to the truth.",
    "<b>Inference</b> \u2014 using the trained numbers to make a prediction on a "
    "<i>new</i> example. On the ESP32, inference is the only part that runs.",
]))
story.append(P(
    "The whole game of ML is <b>generalisation</b>: doing well on examples you "
    "have never seen. A model that memorises its training data but fails on new "
    "data is useless. Much of this project is about catching exactly that "
    "failure \u2014 you will see it again in Section 4."))
story.append(callout(
    "Beginner mental model",
    "Think of the model as a picky recipe-taster. You show it many dishes "
    "labelled \u201cgood\u201d or \u201cbad\u201d. It learns which flavours "
    "matter. Later it tastes a new dish and guesses. If you accidentally taught "
    "it to judge by the colour of the plate instead of the food, it fails on a "
    "differently-coloured plate. That \u201cwrong cue\u201d problem is real, and "
    "it happened to us (Section 4)."))

# ---------------------------------------------------------------- 3
story.append(P("3. The data: what we measured and why", H1))
story.append(hr())
story.append(P(
    "Good ML is mostly good data. We measure five things at the same moment, "
    "repeatedly, and stack them into short time windows."))
story.append(P("The five channels", H2))
story.append(table([
    ["Channel", "Sensor", "What it captures", "Why it matters"],
    ["ax, ay, az", "MPU6050 accel", "Vibration on 3 axes",
     "Imbalance shows up as a strong vibration spike"],
    ["current_mA", "INA228 monitor", "Motor current draw",
     "Friction pulls much more current"],
    ["rpm", "Magnetic encoder", "Rotation speed",
     "Faults change the speed; a shared context signal"],
], [26 * mm, 34 * mm, 38 * mm, 67 * mm], font_size=8.5))
story.append(P(
    "Notice what is <b>not</b> in that list: supply voltage. That omission is "
    "deliberate and is one of the most important lessons in the whole project "
    "\u2014 see Section 4."))
story.append(P("From time-series to examples (windowing)", H2))
story.append(P(
    "A model cannot eat an endless stream. We chop the stream into overlapping "
    "windows: <b>50 samples, step 25</b> (50% overlap). At a 50 Hz sample rate "
    "that is <b>1 second per window</b>. Each window becomes one labelled "
    "example:"))
story.append(code_block([
    "window shape = (50 timesteps, 5 channels)",
    "overlap      = 50% (step 25)",
    "sampling     = 50 Hz  ->  1 s per window",
    "label        = healthy | imbalanced | friction",
]))
story.append(P(
    "The RPM is also duplicated into every timestep of the window as a 5th "
    "channel, so the model sees the motor\u2019s speed alongside its vibration "
    "and current. In firmware the RPM is scaled by measured supply voltage "
    "first, so the model sees a consistent RPM at 12 V, 13 V or 14 V."))
story.append(P("Where the labels come from", H2))
story.append(bullets([
    "<b>healthy</b> \u2014 stock motor, nothing added.",
    "<b>imbalanced</b> \u2014 a ~3 g washer taped off-centre on the output shaft.",
    "<b>friction</b> \u2014 a finger or strap pressing the shaft, visibly slowing it.",
    "Each state is captured for 20 seconds per file, 9 files total, at 12\u201314 V.",
]))

# ---------------------------------------------------------------- 4
story.append(P("4. The variables that matter most", H1))
story.append(hr())
story.append(P(
    "This is the heart of the project \u2014 and the part most beginners "
    "underestimate. Choosing and vetting the right input variables "
    "(<b>features</b>) matters more than picking a fancy model."))
story.append(P("Golden rule: feed the model causes, not coincidences", H2))
story.append(P(
    "Our first model used <b>six</b> channels, including supply voltage. Offline "
    "it scored a great 92.9%. On the real device it failed completely \u2014 "
    "every window was labelled \u201cfriction\u201d. Why? Because the bench "
    "supply happened to sit at a slightly different voltage when faults were "
    "captured. The model learned to read <i>voltage</i> as a proxy for fault, "
    "not the vibration or current. A 20 mV difference was enough to flip every "
    "prediction."))
story.append(callout(
    "Shortcut learning / feature leakage",
    "When a model latches onto an easy-but-wrong cue that happens to correlate "
    "with the label in your training set. Voltage \u201cpredicted\u201d faults "
    "only because of how the data was collected. On a battery or a different "
    "supply, the model breaks. The fix: remove the leaked feature and retrain."))
story.append(P("What changed", H2))
story.append(table([
    ["Model", "Channels", "Params", "Size", "Offline", "On hardware?"],
    ["v2 (6-ch)", "ax, ay, az, current, rpm, voltage", "1003", "5.8 KB",
     "92.9%", "No \u2014 collapses on a voltage shift"],
    ["v3 (5-ch)", "ax, ay, az, current, rpm", "963", "5.6 KB",
     "96.6% \u2192 100%*", "Yes \u2014 robust"],
], [20 * mm, 48 * mm, 14 * mm, 15 * mm, 26 * mm, 42 * mm], font_size=7.5))
story.append(P("*100% is on the JGA25 dataset (117/117 test windows); see the "
               "caveat in Section 9.", SMALL))
story.append(P("So which variables matter?", H2))
story.append(bullets([
    "<b>Vibration (ax, ay, az)</b> \u2014 the main signature of imbalance. A "
    "washing-machine wobble shows up here loudly.",
    "<b>Current</b> \u2014 the main signature of friction. Grit or a rub means "
    "the motor must pull more amps.",
    "<b>RPM</b> \u2014 shared context: a fault that slows the motor changes RPM "
    "in a distinctive way.",
    "<b>Voltage</b> \u2014 <i>excluded</i>. It is a board condition, not a "
    "motor-health cause, and it leaked.",
]))
story.append(P("Other variables you must control (not feed, but manage)", H2))
story.append(bullets([
    "<b>Window length & overlap</b> \u2014 shorter windows react faster but see "
    "less pattern; we chose 1 s.",
    "<b>Sampling rate</b> \u2014 too slow misses vibration detail; 50 Hz matched "
    "the physics and the chip.",
    "<b>Normalisation (mean/std)</b> \u2014 every channel is standardised so no "
    "one unit (like current in mA) dominates. The exact mean/std used in training "
    "are baked into the firmware so inference matches.",
    "<b>Mount & sensor placement</b> \u2014 change these and the vibration "
    "distribution changes (more on this next).",
]))
story.append(callout(
    "A second real failure: changing the motor",
    "We later swapped the small TT motor for the stronger JGA25-370 and "
    "re-mounted the sensor. The TT-trained model dropped to 30.8% \u2014 healthy "
    "and imbalanced swapped completely \u2014 because the vibration fingerprint "
    "moved with the mount. Friction still worked (92%) because current draw is "
    "physical and transfers. Lesson: a model learns the <i>conditions it was "
    "trained on</i>, not an abstract idea of \u201cfault\u201d. Retraining on the "
    "new rig restored it to 100%."))
story.append(PageBreak())

# ---------------------------------------------------------------- 5
story.append(P("5. Why a 1D CNN specifically?", H1))
story.append(hr())
story.append(P(
    "There are many model families: fully-connected networks, classic ML (SVM, "
    "random forest), recurrent networks (LSTM), transformers, and convolutional "
    "neural networks (CNN). Here is why we picked a <b>1D CNN</b>."))
story.append(P("What a 1D convolution does", H2))
story.append(P(
    "A 1D CNN slides small learnable \u201cfilters\u201d along the time axis. "
    "Each filter is a tiny pattern detector \u2014 say, a short hump or a "
    "spike-shaped repetition. Stacking filters lets the model build up more "
    "complex patterns (a spike inside a rhythm) from simple ones. Crucially, a "
    "filter is applied at <i>every</i> position with the <i>same</i> weights, so "
    "the model finds a pattern <b>wherever</b> it occurs in time."))
story.append(P("Why this fits our problem", H2))
story.append(bullets([
    "<b>It is time-series, and local patterns matter.</b> Vibration and current "
    "are signals; faults are shapes that repeat in time. Convolutions are built "
    "for exactly that.",
    "<b>Translation invariance.</b> The same fault pattern a bit earlier or later "
    "should be recognised identically \u2014 convolution gives this for free.",
    "<b>Few parameters.</b> A CNN shares weights across time, so the whole model "
    "is only <b>963 parameters (~5.6 KB)</b> \u2014 perfect for a chip with "
    "little memory.",
    "<b>Fast & cheap to convert.</b> Standard convolutions + pooling + one dense "
    "layer convert cleanly to INT8 TFLite for microcontrollers. No exotic ops "
    "that the tiny runtime cannot handle.",
    "<b>Robust with small data.</b> With only 9 capture files, a small CNN "
    "trained with augmentation generalises better than a huge network that would "
    "overfit.",
]))
story.append(P("Trade-offs vs alternatives", H2))
story.append(table([
    ["Approach", "Pros", "Why not chosen here"],
    ["Fully-connected (MLP)", "Simple", "Ignores time order; many params; overfits small data"],
    ["SVM / Random Forest", "Strong on small data, classic",
     "Needs hand-crafted features (FFT, stats); harder to port as one tiny TFLM model"],
    ["LSTM / RNN", "Good for sequences", "Larger, slower, awkward to quantise & run on MCU"],
    ["Transformer", "State of the art on huge data", "Way too big; we have 9 files, not 9 million"],
    ["1D CNN (chosen)", "Local patterns, tiny, fast, MCU-friendly", "\u2014"],
], [30 * mm, 45 * mm, 90 * mm], font_size=8))
story.append(P("The deployed architecture (v3)", H2))
story.append(code_block([
    "Input        5 channels x 50 timesteps",
    "  Conv1d(5->8,  k=5) + BatchNorm + ReLU + MaxPool(2)",
    "  Conv1d(8->16, k=5) + BatchNorm + ReLU + MaxPool(2)",
    "  Global Average Pooling        -> 16 features",
    "  Dropout(0.5)",
    "  Linear(16 -> 3)               -> healthy / imbalanced / friction",
    "",
    "Total params: 963      Model size: ~5.6 KB (INT8)",
]))
story.append(P(
    "BatchNorm stabilises and speeds up training. Global Average Pooling shrinks "
    "the feature map to one number per filter (and keeps the model tiny). "
    "Dropout(0.5) is a regulariser that prevents memorising. The final Linear "
    "layer produces 3 scores (\u201clogits\u201d); the highest wins."))

# ---------------------------------------------------------------- 6
story.append(P("6. The training method, step by step", H1))
story.append(hr())
story.append(P(
    "Training is a loop: predict \u2192 measure error \u2192 nudge weights \u2192 "
    "repeat. Here is exactly how this project does it, with the reasoning a "
    "beginner needs."))
story.append(P("The pieces", H2))
story.append(bullets([
    "<b>Loss = Cross-Entropy.</b> The standard error measure for picking one of "
    "several classes. Big loss when the model is confidently wrong; small when "
    "confidently right.",
    "<b>Optimiser = Adam (lr = 1e-3, weight_decay = 1e-3).</b> Adam adjusts each "
    "weight by a smart, adaptive step. The small weight decay gently discourages "
    "oversized weights (a mild guard against overfitting).",
    "<b>Batch size = 32.</b> The model looks at 32 windows, averages the error, "
    "and updates once. Efficient and stable.",
    "<b>Epochs = up to 80, with early stopping (patience 15).</b> One epoch = one "
    "full pass over the data. If validation loss stops improving for 15 epochs, "
    "stop and keep the best model.",
    "<b>Split by capture file, not random windows.</b> Test files come from "
    "captures the model never saw \u2014 otherwise overlapping windows would leak "
    "into the test set and inflate accuracy.",
]))
story.append(P("Data augmentation \u2014 fighting overfitting the honest way", H2))
story.append(P(
    "With little data, a model tends to memorise. We create extra training "
    "examples by <b>scaling the vibration channels by \u00b15\u201315%</b>. This "
    "simulates real-world drift: a warmer motor, a slightly looser screw, a "
    "different mounting torque. The test set is <b>never</b> augmented \u2014 it "
    "must stay a fair exam."))
story.append(code_block([
    "# training windows only (simulate day-to-day physical drift)",
    "aug_plus  = window;  aug_plus[:,0:3]  *= uniform(1.05, 1.15)",
    "aug_minus = window;  aug_minus[:,0:3] *= uniform(0.85, 0.95)",
]))
story.append(P("How we know it learned (evaluation)", H2))
story.append(bullets([
    "<b>Accuracy</b> \u2014 fraction correct.",
    "<b>Confusion matrix</b> \u2014 which classes get mixed up (more useful than "
    "accuracy alone).",
    "<b>Per-class F1-score</b> \u2014 balances precision and recall, important "
    "when classes are uneven.",
    "<b>Loss curves</b> \u2014 train vs. validation. A widening gap signals "
    "overfitting.",
]))
story.append(callout(
    "The most important habit",
    "Test on data that is genuinely different (different capture, different day, "
    "different mount). Keep a separate \u201cexam\u201d set and never train on "
    "it. Our 100% number is real on its test set \u2014 but see the caveat in "
    "Section 9 about how \u201cunseen\u201d it truly is."))

# Guide body B: sections 7-9 + build.

# ---------------------------------------------------------------- 7
story.append(PageBreak())
story.append(P("7. The full ML pipeline", H1))
story.append(hr())
story.append(P(
    "A model is only one step. The pipeline is the assembly line that turns raw "
    "sensor files into a model that runs on the chip. Every stage has a matching "
    "script in the repo."))
story.append(P("Stage 1 \u2014 Collect", H2))
story.append(P(
    "Flash the collector firmware, run the motor in each state at 12\u201314 V, "
    "and save sensor rows to CSV (50 Hz). Result: healthy_1..3, imbalanced_1..3, "
    "friction_1..3 \u2014 9 files x 1000 rows x 20 s."))
story.append(P("Stage 2 \u2014 Preprocess", H2))
story.append(P(
    "src/training/preprocess.py loads the CSVs, slices overlapping windows (50 "
    "samples, step 25), appends RPM as a channel, splits train/test by file, "
    "augments the training windows (\u00b15\u201315%), and standardises with the "
    "training mean/std. It saves the arrays plus the mean/std so inference can "
    "reuse them."))
story.append(P("Stage 3 \u2014 Train", H2))
story.append(P(
    "src/training/train.py builds the 1D CNN, trains with Adam + cross-entropy, "
    "early-stops on validation loss, and saves the best checkpoint. It also "
    "writes a confusion matrix, loss curves, and a metrics JSON into results/."))
story.append(P("Stage 4 \u2014 Convert to INT8", H2))
story.append(P(
    "The trained PyTorch weights are exported to a TFLite model and quantised to "
    "INT8 using a small representative dataset. Quantisation shrinks ~10 KB to "
    "~5.6 KB and speeds up inference ~30%, with essentially no accuracy loss on "
    "this model."))
story.append(P("Stage 5 \u2014 Embed in firmware", H2))
story.append(P(
    "The .tflite bytes become a C array (include/model_data.h) and the "
    "normalisation constants become include/norm_params.h. The firmware runs "
    "TFLM: read sensors \u2192 fill a 50-sample window \u2192 normalise \u2192 "
    "invoke \u2192 show the class on the OLED/serial."))
story.append(P("Stage 6 \u2014 Deploy & verify on device", H2))
story.append(P(
    "Flash the ESP32-C3, inject physical faults (cardboard friction, coin "
    "imbalance), and check the live predictions and the measured inference time "
    "(27.9 ms). CI rebuilds and re-tests everything on every push; tagged "
    "releases attach the merged firmware binary."))
story.append(P("The pipeline in one picture", H2))
story.append(code_block([
    "raw CSV  ->  windows + RPM channel + augmentation + normalise",
    "         ->  1D CNN training (Adam, early stop)",
    "         ->  INT8 TFLite (quantise)",
    "         ->  model_data.h + norm_params.h",
    "         ->  ESP32-C3 firmware (TFLM)  ->  live class @ 1 Hz",
]))
story.append(P("Reproduce end-to-end from the repo root:"))
story.append(code_block([
    "python src/training/preprocess.py    # CSV -> windowed arrays",
    "python src/training/train.py         # train + evaluate",
    "# export INT8 TFLite, then regenerate model_data.h",
    "cd src/inference && pio run           # build firmware",
    "pio run -t upload                     # flash to ESP32-C3",
]))

# ---------------------------------------------------------------- 8
story.append(P("8. Getting it onto a microcontroller", H1))
story.append(hr())
story.append(P(
    "This is the \u201cedge\u201d in edge AI \u2014 and where most desktop-trained "
    "models die. The ESP32-C3 has roughly 400 KB of RAM and a few MB of flash, no "
    "operating system, and runs at 160 MHz. Three things make a model fit: small "
    "size, quantisation, and a tiny runtime."))
story.append(P("1. INT8 quantisation", H2))
story.append(P(
    "Each weight is stored as an 8-bit integer instead of a 32-bit float. That is "
    "~4x smaller, uses cheaper integer maths, and runs faster. We calibrate with "
    "representative data so the int8 model behaves almost exactly like the float "
    "one (here: lossless)."))
story.append(P("2. TFLite Micro (TFLM)", H2))
story.append(P(
    "A cut-down runtime designed for microcontrollers, with no dynamic memory and "
    "no OS \u2014 just a fixed memory arena and the operators your model needs. "
    "Your .tflite file is embedded as a C array in flash."))
story.append(P("3. Latency budget", H2))
story.append(table([
    ["Per 1-second cycle", "Time"],
    ["Sensor sampling (one 50-sample window @ 50 Hz)", "20 ms"],
    ["Model inference", "27.9 ms"],
    ["Serial I/O", "~10 ms"],
    ["Total used", "~58 ms"],
    ["Idle headroom", "~942 ms (94%)"],
], [120 * mm, 45 * mm], font_size=9))
story.append(P(
    "Inference is effectively deterministic: across 104 runs the spread was only "
    "47 microseconds. That is the signature of a well-optimised INT8 model on "
    "bare metal."))
story.append(callout(
    "Edge realities that are not bugs",
    "A one-second lag between a physical fault and a changed prediction (the "
    "window must fill). Occasional mixed-signal noise during transitions. No "
    "debouncing yet \u2014 a single window drives the output. In production, "
    "require 3\u20135 agreeing windows before reporting a state change. These are "
    "design choices for the firmware state machine, not model failures."))

# ---------------------------------------------------------------- 9
story.append(PageBreak())
story.append(P("9. Project summary", H1))
story.append(hr())
story.append(P("The one-page version of everything above.", SMALL))
story.append(P("Aim", H2))
story.append(P(
    "Detect a failing motor (healthy / imbalanced / friction) from live sensor "
    "data on a tiny, internet-free ESP32-C3."))
story.append(P("Method", H2))
story.append(bullets([
    "5 channels (3-axis vibration, current, RPM) over 1-second windows.",
    "A small 1D CNN (963 parameters) \u2014 2 conv+pool blocks, GAP, dropout, "
    "linear.",
    "Cross-entropy + Adam, early stopping, vibration augmentation.",
    "INT8 quantisation \u2192 ~5.6 KB \u2192 TFLite Micro on the chip.",
]))
story.append(P("Results", H2))
story.append(table([
    ["Metric", "Value"],
    ["Test accuracy (held-out capture)", "100% (117/117)"],
    ["INT8 vs float accuracy", "Lossless"],
    ["Model size", "~5.6 KB"],
    ["Inference time (160 MHz)", "27.9 ms"],
    ["CPU headroom @ 1 Hz", "~94%"],
    ["Inference jitter (104 runs)", "47 \u00b5s"],
], [110 * mm, 55 * mm], font_size=9))
story.append(P("Lessons learned", H2))
story.append(bullets([
    "<b>The feature that hurt most was voltage</b> \u2014 a leaked shortcut. "
    "Remove it and accuracy <i>and</i> robustness both improved.",
    "<b>A model learns the rig it was trained on.</b> Swap the motor/mount and "
    "you must retrain \u2014 physics-carrying signals (current) transfer better "
    "than mount-dependent ones (vibration).",
    "<b>Always test on truly unseen captures</b>, and stay honest about how "
    "\u201cunseen\u201d the test set really is.",
]))
story.append(callout(
    "Honest caveat",
    "The 100% score is on test windows from captures not used in training, but "
    "all from the same recording sessions and rig. Real-world performance across "
    "days, temperatures and mounts will be lower \u2014 that is the next thing "
    "to validate."))

# ---------------------------------------------------------------- BUILD
doc = SimpleDocTemplate(
    os.path.join(HERE, "ML_Guide_for_Motor_Health.pdf"), pagesize=A4,
    leftMargin=22 * mm, rightMargin=22 * mm,
    topMargin=20 * mm, bottomMargin=18 * mm,
    title="ML Guide for Motor Health",
    author="motor-health-edge-ai",
)


def _footer(canvas, doc_):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(22 * mm, 10 * mm, "ML Guide for Motor Health")
    canvas.drawRightString(A4[0] - 22 * mm, 10 * mm, "Page %d" % doc_.page)
    canvas.restoreState()


doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
print("Wrote", os.path.join(HERE, "ML_Guide_for_Motor_Health.pdf"))
